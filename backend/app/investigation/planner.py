from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.history.change_risk import (
    FileChangeStat,
    assess_change_risk,
)
from app.history.guarding_tests import detect_verification_gaps
from app.investigation.intent import IntentNormalizer
from app.investigation.llm import LLMProvider, get_default_llm_provider
from app.investigation.state import (
    ClaimClassification,
    InvestigationClaim,
    InvestigationPlan,
    InvestigationState,
    InvestigationStep,
    PreChangeBrief,
)
from app.models.evidence import Evidence, EvidenceSourceType
from app.models.investigation import Investigation, InvestigationStatus

logger = logging.getLogger(__name__)


class InvestigationEngine:
    """Bounded, stateful Pre-Change Investigation Engine.

    Enforces strict 1-3 model call limits per investigation.
    Runs deterministic gathering and risk calculations prior to LLM reasoning.
    """

    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self.llm = llm_provider or get_default_llm_provider()

    async def initialize_state(
        self,
        investigation_id: uuid.UUID,
        repository_id: uuid.UUID,
        query: str,
        target_path: Optional[str] = None,
        target_symbol: Optional[str] = None,
        known_files: Optional[List[str]] = None,
        known_symbols: Optional[List[str]] = None,
    ) -> InvestigationState:
        """Step 1: Intake & Normalization."""
        intent = IntentNormalizer.normalize(
            raw_query=query,
            target_path=target_path,
            target_symbol=target_symbol,
            known_files=known_files,
            known_symbols=known_symbols,
        )

        return InvestigationState(
            investigation_id=investigation_id,
            repository_id=repository_id,
            query=query,
            step=InvestigationStep.INTAKE,
            intent=intent,
        )

    async def plan(self, state: InvestigationState) -> InvestigationPlan:
        """Step 2: Investigation Planning.

        Uses LLM only if intent is ambiguous and model calls remain within budget.
        """
        state.step = InvestigationStep.PLAN

        if state.intent and state.intent.is_ambiguous and state.can_call_model:
            try:
                plan, tokens = await self.llm.plan_investigation(
                    intent=state.intent,
                    context_preview=f"Query: {state.query}",
                )
                state.record_model_call(
                    prompt_tokens=tokens.get("prompt_tokens", 0),
                    completion_tokens=tokens.get("completion_tokens", 0),
                )
                state.plan = plan
                return plan
            except Exception as e:
                logger.warning(f"Planner LLM call failed, falling back to deterministic: {e}")

        # Deterministic plan
        target_files = state.intent.target_files if state.intent else []
        target_symbols = state.intent.target_symbols if state.intent else []
        plan = InvestigationPlan(
            steps=["target_analysis", "historical_context", "risk_signals", "synthesis"],
            target_files=target_files,
            target_symbols=target_symbols,
            gather_tasks=["ast_context", "git_commits", "engineering_docs", "risk_metrics"],
            reasoning_focus=state.intent.intent_summary if state.intent else state.query,
        )
        state.plan = plan
        return plan

    async def gather(
        self,
        state: InvestigationState,
        db: AsyncSession,
        file_commits: Optional[List[Dict[str, Any]]] = None,
        code_snippets: Optional[List[Dict[str, Any]]] = None,
        engineering_docs: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Step 3: Deterministic Evidence & Risk Metric Gathering."""
        state.step = InvestigationStep.GATHER
        evidence_items: List[Dict[str, Any]] = []
        signals: Dict[str, Any] = {}

        target_files = state.intent.target_files if state.intent else []
        target_symbols = state.intent.target_symbols if state.intent else []

        # 1. Gather code evidence
        if code_snippets:
            for snippet in code_snippets:
                ev = {
                    "id": f"ev-code-{len(evidence_items) + 1}",
                    "source_type": EvidenceSourceType.CODE,
                    "source_id": snippet.get("path", "unknown"),
                    "title": f"Code: {snippet.get('path')}",
                    "snippet": snippet.get("code", "")[:400],
                    "path": snippet.get("path"),
                    "line_start": snippet.get("line_start"),
                    "line_end": snippet.get("line_end"),
                    "confidence": 1.0,
                }
                evidence_items.append(ev)
        elif target_files:
            for tf in target_files:
                ev = {
                    "id": f"ev-code-{len(evidence_items) + 1}",
                    "source_type": EvidenceSourceType.CODE,
                    "source_id": tf,
                    "title": f"Target File: {tf}",
                    "snippet": f"Target file identified for change: {tf}",
                    "path": tf,
                    "confidence": 1.0,
                }
                evidence_items.append(ev)

        # 2. Gather commit history evidence
        if file_commits:
            for commit in file_commits[:5]:
                ev = {
                    "id": f"ev-commit-{len(evidence_items) + 1}",
                    "source_type": EvidenceSourceType.COMMIT,
                    "source_id": commit.get("hash", "unknown"),
                    "title": f"Commit: {commit.get('hash', '')[:7]} - {commit.get('message', '')[:60]}",
                    "snippet": commit.get("message", ""),
                    "confidence": 0.95,
                    "extra_metadata": {"author": commit.get("author")},
                }
                evidence_items.append(ev)

        # 3. Gather documentation / ADR evidence
        if engineering_docs:
            for doc in engineering_docs:
                ev = {
                    "id": f"ev-doc-{len(evidence_items) + 1}",
                    "source_type": EvidenceSourceType.DOC,
                    "source_id": doc.get("id", "doc"),
                    "title": doc.get("title", "Engineering Document"),
                    "snippet": doc.get("summary", "")[:300],
                    "confidence": 0.9,
                }
                evidence_items.append(ev)

        # 4. Compute deterministic risk & co-change signals
        if target_files:
            file_stats = [
                FileChangeStat(path=tf, lines_added=50, lines_deleted=10)
                for tf in target_files
            ]
            risk_report = assess_change_risk(file_stats)
            signals["change_risk"] = {
                "risk_score": risk_report.risk_score,
                "risk_level": risk_report.risk_level,
                "lines_added": risk_report.kamei_metrics.lines_added,
                "lines_deleted": risk_report.kamei_metrics.lines_deleted,
                "file_count": risk_report.kamei_metrics.files_touched,
                "shannon_entropy": risk_report.kamei_metrics.shannon_entropy,
                "explanatory_factors": risk_report.explanatory_factors,
            }

            # Guarding tests check
            untested_warns, stale_warns = detect_verification_gaps(
                proposed_files=set(target_files),
                file_to_covering_tests={},
            )
            signals["guarding_tests"] = {
                "untested_files": [w.target_file for w in untested_warns],
                "has_coverage_gaps": len(untested_warns) > 0,
            }

        state.gathered_evidence = evidence_items
        state.gathered_signals = signals
        state.gathered_context = {
            "target_files": target_files,
            "target_symbols": target_symbols,
            "evidence_count": len(evidence_items),
        }
        return signals

    async def reason(self, state: InvestigationState) -> List[InvestigationClaim]:
        """Step 4: Bounded Reasoning & Claim Generation."""
        state.step = InvestigationStep.REASON

        if not state.can_call_model:
            # Model budget reached: fallback to deterministic synthesis
            claims = [
                InvestigationClaim(
                    id="claim-fallback-1",
                    classification=ClaimClassification.FACT,
                    statement=f"Investigation target: {state.intent.intent_summary if state.intent else state.query}",
                    evidence_ids=[e["id"] for e in state.gathered_evidence[:1]],
                    confidence=1.0,
                )
            ]
            state.claims = claims
            return claims

        # Prepare context summary
        context_str = f"Intent: {state.intent.raw_query if state.intent else state.query}\n"
        context_str += f"Target Files: {state.intent.target_files if state.intent else []}\n"
        context_str += f"Evidence Items: {len(state.gathered_evidence)}\n"
        for e in state.gathered_evidence[:5]:
            context_str += f"- [{e['id']}] {e['title']}: {e['snippet'][:100]}\n"

        try:
            summary, claims, tokens = await self.llm.reason_investigation(
                intent=state.intent or IntentNormalizer.normalize(state.query),
                gathered_context=context_str,
                signals=state.gathered_signals,
                evidence_catalog=state.gathered_evidence,
            )
            state.record_model_call(
                prompt_tokens=tokens.get("prompt_tokens", 0),
                completion_tokens=tokens.get("completion_tokens", 0),
            )
            state.claims = claims
            return claims
        except Exception as e:
            logger.warning(f"Reasoner LLM call failed, fallback: {e}")
            claims = [
                InvestigationClaim(
                    id="claim-1",
                    classification=ClaimClassification.FACT,
                    statement=f"Proposed change affects {state.intent.target_files if state.intent else 'targets'}.",
                    evidence_ids=[e["id"] for e in state.gathered_evidence[:1]],
                    confidence=0.9,
                )
            ]
            state.claims = claims
            return claims

    async def verify(self, state: InvestigationState) -> List[InvestigationClaim]:
        """Step 5: Claim Verification against Gathered Evidence."""
        state.step = InvestigationStep.VERIFY

        verified_claims, tokens = await self.llm.verify_claims(
            claims=state.claims,
            evidence_catalog=state.gathered_evidence,
        )
        if tokens.get("prompt_tokens") or tokens.get("completion_tokens"):
            if state.can_call_model:
                state.record_model_call(
                    prompt_tokens=tokens.get("prompt_tokens", 0),
                    completion_tokens=tokens.get("completion_tokens", 0),
                )
        state.claims = verified_claims
        return verified_claims

    async def synthesize(
        self,
        state: InvestigationState,
        db: AsyncSession,
    ) -> PreChangeBrief:
        """Step 6: Pre-Change Investigation Brief Assembly & Database Persistence."""
        state.step = InvestigationStep.SYNTHESIZE

        # Extract unknowns and checks
        unknowns: List[str] = [
            c.statement for c in state.claims if c.classification == ClaimClassification.UNKNOWN
        ]
        if not unknowns and state.gathered_signals.get("guarding_tests", {}).get("untested_files"):
            unknowns.append(
                f"Untested files detected: {', '.join(state.gathered_signals['guarding_tests']['untested_files'])}"
            )

        recommended_checks = [
            "Verify all inbound callers before modifying interface signatures.",
            "Run guarding test suite covering modified symbols.",
        ]
        if state.gathered_signals.get("change_risk", {}).get("shannon_entropy", 0) > 1.5:
            recommended_checks.append("High churn entropy detected: ensure changes remain modular.")

        brief = PreChangeBrief(
            summary=(
                f"Investigation of '{state.query}' completed with {len(state.claims)} verified claims "
                f"across {len(state.gathered_evidence)} evidence items."
            ),
            intent_summary=state.intent.intent_summary if state.intent else state.query,
            target_files=state.intent.target_files if state.intent else [],
            target_symbols=state.intent.target_symbols if state.intent else [],
            claims=state.claims,
            signals=state.gathered_signals,
            constraints=[],
            unknowns=unknowns,
            recommended_checks=recommended_checks,
            model_calls_count=state.model_calls_count,
            token_usage=state.token_usage,
        )
        state.brief = brief
        state.step = InvestigationStep.COMPLETED

        # Persist to DB Investigation record
        inv = await db.get(Investigation, state.investigation_id)
        if inv:
            inv.status = InvestigationStatus.COMPLETED
            inv.summary = brief.summary
            inv.answer = brief.intent_summary
            inv.claims = [
                {
                    "id": c.id,
                    "classification": c.classification.value,
                    "statement": c.statement,
                    "evidence_ids": c.evidence_ids,
                    "confidence": c.confidence,
                }
                for c in state.claims
            ]
            inv.token_usage = state.token_usage
            inv.latency_ms = state.latency_ms

            # Persist Evidence records
            for ev_data in state.gathered_evidence:
                ev_record = Evidence(
                    investigation=inv,
                    source_type=ev_data["source_type"],
                    source_id=ev_data["source_id"],
                    title=ev_data["title"],
                    snippet=ev_data["snippet"],
                    path=ev_data.get("path"),
                    line_start=ev_data.get("line_start"),
                    line_end=ev_data.get("line_end"),
                    confidence=ev_data.get("confidence", 1.0),
                    extra_metadata=ev_data.get("extra_metadata", {}),
                )
                db.add(ev_record)

            await db.commit()
            await db.refresh(inv, attribute_names=["evidence"])

        return brief

    async def run(
        self,
        investigation_id: uuid.UUID,
        db: AsyncSession,
        target_path: Optional[str] = None,
        target_symbol: Optional[str] = None,
        code_snippets: Optional[List[Dict[str, Any]]] = None,
        file_commits: Optional[List[Dict[str, Any]]] = None,
        engineering_docs: Optional[List[Dict[str, Any]]] = None,
    ) -> InvestigationState:
        """Run bounded investigation pipeline end-to-end."""
        start_time = time.perf_counter()

        inv = await db.get(Investigation, investigation_id)
        if not inv:
            raise ValueError(f"Investigation {investigation_id} not found")

        inv.status = InvestigationStatus.PLANNING
        await db.commit()

        state = await self.initialize_state(
            investigation_id=inv.id,
            repository_id=inv.repository_id,
            query=inv.query,
            target_path=target_path,
            target_symbol=target_symbol,
        )

        try:
            await self.plan(state)
            inv.status = InvestigationStatus.GATHERING
            await db.commit()

            await self.gather(
                state=state,
                db=db,
                file_commits=file_commits,
                code_snippets=code_snippets,
                engineering_docs=engineering_docs,
            )

            inv.status = InvestigationStatus.REASONING
            await db.commit()

            await self.reason(state)
            await self.verify(state)

            state.latency_ms = int((time.perf_counter() - start_time) * 1000)
            await self.synthesize(state, db)

        except Exception as e:
            logger.exception(f"Investigation execution failed: {e}")
            state.step = InvestigationStep.FAILED
            state.errors.append(str(e))
            inv.status = InvestigationStatus.FAILED
            await db.commit()

        return state
