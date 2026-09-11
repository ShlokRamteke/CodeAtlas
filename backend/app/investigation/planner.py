from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.history.change_risk import (
    FileChangeStat,
    HistoricalCommitInfo,
    assess_change_risk,
    compute_defect_pressure,
    is_fix_commit,
    mine_defect_pressure_from_db,
    parse_unified_diff,
)
from app.history.co_change import (
    detect_hidden_coupling,
    mine_co_change_partners,
)
from app.history.guarding_tests import (
    analyze_guarding_tests,
    build_test_coverage_mapping,
    detect_verification_gaps,
    is_test_file,
)
from app.investigation.blast_radius import BlastRadiusAnalyzer
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
from app.models.commit import Commit
from app.models.commit_file_change import CommitFileChange
from app.models.dependency import CodeDependency
from app.models.evidence import Evidence, EvidenceSourceType
from app.models.investigation import Investigation, InvestigationStatus
from app.models.source_file import SourceFile

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
        diff: Optional[str] = None,
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

        if diff:
            parsed = parse_unified_diff(diff)
            for ps in parsed:
                if ps.path not in intent.target_files:
                    intent.target_files.append(ps.path)

        return InvestigationState(
            investigation_id=investigation_id,
            repository_id=repository_id,
            query=query,
            diff=diff,
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

        # 4. Compute deterministic blast radius, risk, and co-change signals
        if target_files:
            # Query static dependencies for repository
            dep_query = select(CodeDependency).where(
                CodeDependency.repository_id == state.repository_id
            )
            dep_res = await db.execute(dep_query)
            db_deps = dep_res.scalars().all()
            static_edges = [(d.source_path, d.target_path) for d in db_deps]

            # Query source files to discover all test files in repository
            sf_query = select(SourceFile.path).where(
                SourceFile.repository_id == state.repository_id
            )
            sf_res = await db.execute(sf_query)
            all_repo_files = [r for r in sf_res.scalars().all()]

            # Compute Blast Radius
            blast_radius = BlastRadiusAnalyzer.compute_blast_radius(
                target_files=target_files,
                dependency_edges=static_edges,
                max_depth=3,
            )
            signals["blast_radius"] = {
                "target_files": blast_radius.target_files,
                "upstream_callers": [
                    {
                        "path": n.path,
                        "depth": n.depth,
                        "direction": n.direction,
                        "via": n.via,
                        "component": n.component,
                    }
                    for n in blast_radius.upstream_callers
                ],
                "downstream_dependencies": [
                    {
                        "path": n.path,
                        "depth": n.depth,
                        "direction": n.direction,
                        "via": n.via,
                        "component": n.component,
                    }
                    for n in blast_radius.downstream_dependencies
                ],
                "transitive_files": blast_radius.transitive_files,
                "affected_components": blast_radius.affected_components,
                "max_depth_reached": blast_radius.max_depth_reached,
                "total_affected_count": blast_radius.total_affected_count,
            }

            # Add blast radius evidence if callers or callees found
            if blast_radius.upstream_callers:
                ev = {
                    "id": f"ev-blast-up-{len(evidence_items) + 1}",
                    "source_type": EvidenceSourceType.CODE,
                    "source_id": "blast-radius-upstream",
                    "title": f"Upstream Callers ({len(blast_radius.upstream_callers)} files)",
                    "snippet": f"Direct and transitive upstream callers: {', '.join(n.path for n in blast_radius.upstream_callers[:5])}",
                    "confidence": 1.0,
                    "extra_metadata": {"affected_count": len(blast_radius.upstream_callers)},
                }
                evidence_items.append(ev)

            # Query historical commit diffs for co-change mining
            cfc_query = (
                select(CommitFileChange.commit_id, CommitFileChange.file_path, Commit.committed_at)
                .join(Commit, CommitFileChange.commit_id == Commit.id)
                .where(Commit.repository_id == state.repository_id)
                .order_by(Commit.committed_at.desc())
            )
            cfc_res = await db.execute(cfc_query)
            cfc_rows = cfc_res.all()

            commit_files_map: Dict[uuid.UUID, Set[str]] = defaultdict(set)
            commit_time_map: Dict[uuid.UUID, datetime] = {}
            for c_id, f_path, c_time in cfc_rows:
                if f_path:
                    commit_files_map[c_id].add(f_path)
                    commit_time_map[c_id] = c_time

            commit_diff_tuples = [
                (files, commit_time_map[c_id]) for c_id, files in commit_files_map.items()
            ]

            co_change_matrix = mine_co_change_partners(
                commit_file_sets=commit_diff_tuples,
                min_co_changes=2,
                min_frequency=0.5,
                half_life_days=180.0,
            )

            known_static_set = set(static_edges)
            hidden_warnings = detect_hidden_coupling(
                proposed_files=set(target_files),
                co_change_matrix=co_change_matrix,
                known_static_edges=known_static_set,
            )

            signals["co_change"] = {
                "hidden_coupling_warnings": [
                    {
                        "target_file": w.target_file,
                        "omitted_partner": w.omitted_partner,
                        "frequency": w.frequency,
                        "co_change_count": w.co_change_count,
                        "has_static_import": w.has_static_import,
                        "explanation": w.explanation,
                    }
                    for w in hidden_warnings
                ],
                "has_hidden_coupling": any(not w.has_static_import for w in hidden_warnings),
            }

            for hw in hidden_warnings:
                ev = {
                    "id": f"ev-coupling-{len(evidence_items) + 1}",
                    "source_type": EvidenceSourceType.COMMIT,
                    "source_id": hw.omitted_partner,
                    "title": f"{'Hidden Coupling' if not hw.has_static_import else 'Coupled Partner'}: {hw.omitted_partner}",
                    "snippet": hw.explanation,
                    "confidence": 0.9,
                    "extra_metadata": {
                        "target_file": hw.target_file,
                        "frequency": hw.frequency,
                        "co_change_count": hw.co_change_count,
                    },
                }
                evidence_items.append(ev)

            # Quantitative Change Risk & Defect Pressure calculation
            file_stats: list[FileChangeStat] = []
            if state.diff:
                parsed_stats = parse_unified_diff(state.diff)
                if parsed_stats:
                    file_stats = parsed_stats

            if not file_stats and target_files:
                # Query historical average insertions/deletions from CommitFileChange if available
                clean_target_set = {f.lstrip("/") for f in target_files}
                cfc_stats_query = (
                    select(
                        CommitFileChange.file_path,
                        CommitFileChange.insertions,
                        CommitFileChange.deletions,
                    )
                    .join(Commit, CommitFileChange.commit_id == Commit.id)
                    .where(
                        Commit.repository_id == state.repository_id,
                        CommitFileChange.file_path.in_(clean_target_set),
                    )
                )
                cfc_stats_res = await db.execute(cfc_stats_query)
                cfc_stat_rows = cfc_stats_res.all()

                per_file_avg: dict[str, list[tuple[int, int]]] = defaultdict(list)
                for f_path, ins, dels in cfc_stat_rows:
                    per_file_avg[f_path].append((ins, dels))

                for tf in target_files:
                    clean_tf = tf.lstrip("/")
                    if clean_tf in per_file_avg and per_file_avg[clean_tf]:
                        entries = per_file_avg[clean_tf]
                        avg_ins = max(1, sum(x[0] for x in entries) // len(entries))
                        avg_del = max(0, sum(x[1] for x in entries) // len(entries))
                        file_stats.append(
                            FileChangeStat(
                                path=clean_tf, lines_added=avg_ins, lines_deleted=avg_del
                            )
                        )
                    else:
                        file_stats.append(
                            FileChangeStat(path=clean_tf, lines_added=50, lines_deleted=10)
                        )

            # Mine historical defect pressure (deep walk up to 20,000 commits with half-life = 365d)
            if file_commits:
                mock_historical_commits = [
                    HistoricalCommitInfo(
                        hash=fc.get("hash", f"c{i}"),
                        message=fc.get("message", ""),
                        timestamp=fc.get("timestamp", datetime.now()),
                        touched_files=tuple(fc.get("touched_files", ())),
                        is_fix=fc.get("is_fix", False),
                    )
                    for i, fc in enumerate(file_commits)
                ]
                clean_targets = {f.lstrip("/") for f in target_files}
                defect_pressure = compute_defect_pressure(mock_historical_commits, clean_targets)
                fix_commits = [
                    c
                    for c in mock_historical_commits
                    if (c.is_fix or is_fix_commit(c.message))
                    and any(f in clean_targets for f in c.touched_files)
                ]
            else:
                defect_pressure, fix_commits = await mine_defect_pressure_from_db(
                    db=db,
                    repository_id=state.repository_id,
                    target_files=set(target_files),
                    limit=20000,
                    half_life_days=365.0,
                )

            risk_report = assess_change_risk(
                changes=file_stats,
                commits=fix_commits,
            )

            signals["change_risk"] = {
                "risk_score": risk_report.risk_score,
                "risk_level": risk_report.risk_level,
                "lines_added": risk_report.kamei_metrics.lines_added,
                "lines_deleted": risk_report.kamei_metrics.lines_deleted,
                "file_count": risk_report.kamei_metrics.files_touched,
                "distinct_directories": risk_report.kamei_metrics.distinct_directories,
                "distinct_subsystems": risk_report.kamei_metrics.distinct_subsystems,
                "shannon_entropy": risk_report.kamei_metrics.shannon_entropy,
                "defect_pressure": risk_report.defect_pressure,
                "fix_commit_count": risk_report.fix_commit_count,
                "explanatory_factors": risk_report.explanatory_factors,
            }

            ev_risk = {
                "id": f"ev-risk-{len(evidence_items) + 1}",
                "source_type": EvidenceSourceType.COMMIT,
                "source_id": "kamei-change-risk",
                "title": f"Quantitative Change Risk: {risk_report.risk_level} ({risk_report.risk_score:.2f})",
                "snippet": (
                    f"Kamei Churn: +{risk_report.kamei_metrics.lines_added}/-{risk_report.kamei_metrics.lines_deleted} lines "
                    f"across {risk_report.kamei_metrics.files_touched} files in {risk_report.kamei_metrics.distinct_subsystems} subsystems. "
                    f"Shannon entropy: {risk_report.kamei_metrics.shannon_entropy}. "
                    f"Defect pressure: {risk_report.defect_pressure:.2f} ({risk_report.fix_commit_count} prior fix commits)."
                ),
                "confidence": 1.0,
                "extra_metadata": {
                    "risk_score": risk_report.risk_score,
                    "risk_level": risk_report.risk_level,
                    "kamei_metrics": {
                        "lines_added": risk_report.kamei_metrics.lines_added,
                        "lines_deleted": risk_report.kamei_metrics.lines_deleted,
                        "files_touched": risk_report.kamei_metrics.files_touched,
                        "distinct_directories": risk_report.kamei_metrics.distinct_directories,
                        "distinct_subsystems": risk_report.kamei_metrics.distinct_subsystems,
                        "shannon_entropy": risk_report.kamei_metrics.shannon_entropy,
                    },
                    "defect_pressure": risk_report.defect_pressure,
                    "fix_commit_count": risk_report.fix_commit_count,
                    "explanatory_factors": risk_report.explanatory_factors,
                },
            }
            evidence_items.append(ev_risk)

            # Guarding tests check & verification gap detection
            diff_files = set(target_files) | {f.path for f in file_stats}
            coverage_mapping = build_test_coverage_mapping(
                target_files=set(target_files),
                dependency_edges=static_edges,
                all_files=all_repo_files,
            )
            guarding_report = analyze_guarding_tests(
                proposed_files=set(target_files),
                file_to_covering_tests=coverage_mapping,
                files_in_diff=diff_files,
            )
            signals["guarding_tests"] = guarding_report.to_dict()

            top_ranked = [t.test_file for t in guarding_report.ranked_tests[:3]]
            untested_names = [w.target_file for w in guarding_report.untested_changes[:3]]
            stale_names = [w.target_file for w in guarding_report.stale_test_candidates[:3]]

            ev_tests = {
                "id": f"ev-tests-{len(evidence_items) + 1}",
                "source_type": EvidenceSourceType.CODE,
                "source_id": "guarding-tests",
                "title": f"Guarding Tests ({guarding_report.total_guarding_tests} suites, {len(guarding_report.untested_changes)} untested, {len(guarding_report.stale_test_candidates)} stale)",
                "snippet": (
                    f"Reach-ranked guarding test suites: {', '.join(top_ranked) if top_ranked else 'None'}. "
                    f"Untested files: {', '.join(untested_names) if untested_names else 'None'}. "
                    f"Stale test candidates: {', '.join(stale_names) if stale_names else 'None'}."
                ),
                "confidence": 1.0,
                "extra_metadata": guarding_report.to_dict(),
            }
            evidence_items.append(ev_tests)

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
        recommended_checks: List[str] = [
            "Verify all inbound callers before modifying interface signatures.",
            "Run guarding test suite covering modified symbols.",
        ]
        blast_sig = state.gathered_signals.get("blast_radius", {})
        if blast_sig.get("total_affected_count", 0) > 3:
            affected_comps = blast_sig.get("affected_components", [])
            recommended_checks.append(
                f"Broad blast radius ({blast_sig.get('total_affected_count')} files across {len(affected_comps)} components): stage rollouts incrementally."
            )

        co_change_sig = state.gathered_signals.get("co_change", {})
        hidden_warnings = co_change_sig.get("hidden_coupling_warnings", [])
        if hidden_warnings:
            omitted_list = [w["omitted_partner"] for w in hidden_warnings]
            recommended_checks.append(
                f"Historical co-change coupling: inspect omitted partner files ({', '.join(omitted_list[:3])}) before completing change."
            )
            unknowns.append(
                f"Potential omitted partner files: {', '.join(omitted_list[:3])} frequently co-change with targets."
            )

        guarding_sig = state.gathered_signals.get("guarding_tests", {})
        ranked_tests = guarding_sig.get("ranked_tests", [])
        if ranked_tests:
            top_t = ranked_tests[0]
            recommended_checks.append(
                f"Execute high-reach guarding test suite '{top_t['test_file']}' first (guards {top_t['reached_target_count']} modified target files)."
            )
        stale_candidates = guarding_sig.get("stale_test_candidates", [])
        if stale_candidates:
            stale_w = stale_candidates[0]
            guarding_preview = ", ".join(stale_w["guarding_tests"][:2])
            recommended_checks.append(
                f"Update guarding test suite ({guarding_preview}) to assert modified behavior in '{stale_w['target_file']}'."
            )
        untested_files = guarding_sig.get("untested_files", [])
        if untested_files:
            recommended_checks.append(
                f"Author guarding test coverage for untested targets ({', '.join(untested_files[:3])}) before deployment."
            )
            unknowns.append(
                f"Verification gap: {len(untested_files)} target file(s) lack guarding tests ({', '.join(untested_files[:3])})."
            )

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
        diff: Optional[str] = None,
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
            diff=diff,
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
