from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Protocol, Tuple

import httpx

from app.core.config import settings
from app.investigation.intent import NormalizedChangeIntent
from app.investigation.prompts import (
    PlannerLLMOutput,
    ReasonerLLMOutput,
    build_planner_prompt,
    build_reasoner_prompt,
)
from app.investigation.state import ClaimClassification, InvestigationClaim, InvestigationPlan

logger = logging.getLogger(__name__)


class LLMProvider(Protocol):
    async def plan_investigation(
        self, intent: NormalizedChangeIntent, context_preview: str
    ) -> Tuple[InvestigationPlan, Dict[str, int]]: ...

    async def reason_investigation(
        self,
        intent: NormalizedChangeIntent,
        gathered_context: str,
        signals: Dict[str, Any],
        evidence_catalog: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, List[InvestigationClaim], Dict[str, int], List[Dict[str, Any]]]: ...

    async def verify_claims(
        self, claims: List[InvestigationClaim], evidence_catalog: List[Dict[str, Any]]
    ) -> Tuple[List[InvestigationClaim], Dict[str, int]]: ...


class MockLLMProvider:
    """Deterministic offline mock LLM provider for unit and integration testing."""

    def __init__(
        self,
        mock_plan: Optional[InvestigationPlan] = None,
        mock_claims: Optional[List[InvestigationClaim]] = None,
        mock_summary: str = "Mock synthesis: Change verified with evidence.",
        mock_code_changes: Optional[List[Dict[str, Any]]] = None,
    ):
        self.mock_plan = mock_plan
        self.mock_claims = mock_claims
        self.mock_summary = mock_summary
        self.mock_code_changes = mock_code_changes
        self.calls_count = 0

    async def plan_investigation(
        self, intent: NormalizedChangeIntent, context_preview: str
    ) -> Tuple[InvestigationPlan, Dict[str, int]]:
        self.calls_count += 1
        plan = self.mock_plan or InvestigationPlan(
            steps=["target_resolution", "history_mining", "risk_evaluation"],
            target_files=intent.target_files,
            target_symbols=intent.target_symbols,
            gather_tasks=["gather_ast", "gather_history", "compute_risk"],
            reasoning_focus="Investigate impact, co-change risks, and design constraints.",
        )
        return plan, {"prompt_tokens": 120, "completion_tokens": 45}

    async def reason_investigation(
        self,
        intent: NormalizedChangeIntent,
        gathered_context: str,
        signals: Dict[str, Any],
        evidence_catalog: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, List[InvestigationClaim], Dict[str, int], List[Dict[str, Any]]]:
        self.calls_count += 1
        claims = self.mock_claims or [
            InvestigationClaim(
                id="claim-1",
                classification=ClaimClassification.FACT,
                statement=f"Target {intent.target_files or intent.target_symbols} is referenced in codebase.",
                evidence_ids=["ev-1"],
                confidence=1.0,
            ),
            InvestigationClaim(
                id="claim-2",
                classification=ClaimClassification.INFERENCE,
                statement="Modifying payment interface requires updating downstream handlers.",
                evidence_ids=["ev-1"],
                confidence=0.85,
            ),
            InvestigationClaim(
                id="claim-3",
                classification=ClaimClassification.UNKNOWN,
                statement="External webhook retry semantics cannot be verified from static code.",
                evidence_ids=[],
                confidence=0.5,
            ),
        ]
        code_changes = self.mock_code_changes or [
            {
                "file_path": intent.target_files[0] if intent.target_files else "app/main.py",
                "symbol_name": intent.target_symbols[0] if intent.target_symbols else "handler",
                "action": "modify",
                "description": f"Update implementation for {intent.intent_summary or intent.raw_query}",
                "signature_or_snippet": None,
                "affected_callers": [],
            }
        ]
        return (
            self.mock_summary,
            claims,
            {"prompt_tokens": 250, "completion_tokens": 90},
            code_changes,
        )

    async def verify_claims(
        self, claims: List[InvestigationClaim], evidence_catalog: List[Dict[str, Any]]
    ) -> Tuple[List[InvestigationClaim], Dict[str, int]]:
        self.calls_count += 1
        valid_ev_ids = {str(e.get("id") or e.get("source_id")) for e in evidence_catalog}
        verified_claims: List[InvestigationClaim] = []

        for c in claims:
            valid_citations = [eid for eid in c.evidence_ids if str(eid) in valid_ev_ids]
            if c.classification == ClaimClassification.FACT and not valid_citations:
                downgraded = InvestigationClaim(
                    id=c.id,
                    classification=ClaimClassification.INFERENCE,
                    statement=c.statement,
                    evidence_ids=[],
                    confidence=0.4,
                )
                verified_claims.append(downgraded)
            else:
                verified_claims.append(
                    InvestigationClaim(
                        id=c.id,
                        classification=c.classification,
                        statement=c.statement,
                        evidence_ids=valid_citations,
                        confidence=c.confidence,
                    )
                )

        return verified_claims, {"prompt_tokens": 80, "completion_tokens": 30}


def extract_json_payload(raw_text: str) -> str:
    """Extract clean JSON string from raw model output, stripping markdown fences."""
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


class OpenRouterLLMProvider:
    """Production provider connecting to OpenRouter API with prompt formatting and schema validation."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or settings.OPENROUTER_API_KEY or settings.OPENAI_API_KEY
        self.model = model or settings.OPENROUTER_MODEL or settings.OPENAI_MODEL
        self.base_url = (base_url or settings.OPENROUTER_BASE_URL).rstrip("/")

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://codeatlas.dev",
            "X-Title": "CodeAtlas",
        }

    async def _post_chat_completion(
        self, client: httpx.AsyncClient, messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Send chat completion, falling back gracefully if response_format is unsupported by provider."""
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
        }
        resp = await client.post(
            f"{self.base_url}/chat/completions",
            headers=self.headers,
            json=payload,
        )
        if resp.status_code == 400:
            err_msg = resp.text.lower()
            if (
                "structured-outputs" in err_msg
                or "response_format" in err_msg
                or "invalid_request_body" in err_msg
                or "not support" in err_msg
            ):
                payload.pop("response_format", None)
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                )
        resp.raise_for_status()
        return resp.json()

    async def plan_investigation(
        self, intent: NormalizedChangeIntent, context_preview: str
    ) -> Tuple[InvestigationPlan, Dict[str, int]]:
        if not self.api_key:
            return (
                InvestigationPlan(
                    steps=["gather_context", "evaluate_risk", "synthesize"],
                    target_files=intent.target_files,
                    target_symbols=intent.target_symbols,
                    gather_tasks=["ast", "history", "constraints"],
                    reasoning_focus=f"Evaluate proposed change: {intent.raw_query}",
                ),
                {"prompt_tokens": 0, "completion_tokens": 0},
            )

        sys_prompt, user_msg = build_planner_prompt(intent, context_preview)

        try:
            async with httpx.AsyncClient(timeout=35.0) as client:
                data = await self._post_chat_completion(
                    client,
                    [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_msg},
                    ],
                )
                raw_text = data["choices"][0]["message"]["content"]
                cleaned_json = extract_json_payload(raw_text)
                output = PlannerLLMOutput.model_validate_json(cleaned_json)

                usage = data.get("usage", {})
                tokens = {
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                }

                return (
                    InvestigationPlan(
                        steps=output.steps or ["gather", "reason", "verify"],
                        target_files=output.target_files or intent.target_files,
                        target_symbols=output.target_symbols or intent.target_symbols,
                        gather_tasks=output.gather_tasks or ["ast", "history"],
                        reasoning_focus=output.reasoning_focus or intent.intent_summary,
                    ),
                    tokens,
                )
        except Exception as e:
            logger.warning(f"OpenRouter planning call failed, using fallback: {e}")
            return (
                InvestigationPlan(
                    steps=["gather", "reason", "verify"],
                    target_files=intent.target_files,
                    target_symbols=intent.target_symbols,
                    gather_tasks=["ast", "history"],
                    reasoning_focus=intent.intent_summary,
                ),
                {"prompt_tokens": 0, "completion_tokens": 0},
            )

    async def reason_investigation(
        self,
        intent: NormalizedChangeIntent,
        gathered_context: str,
        signals: Dict[str, Any],
        evidence_catalog: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[str, List[InvestigationClaim], Dict[str, int], List[Dict[str, Any]]]:
        if not self.api_key:
            summary = f"Grounded pre-change investigation for: {intent.raw_query}."
            claims = [
                InvestigationClaim(
                    id="claim-det-1",
                    classification=ClaimClassification.FACT,
                    statement=f"Investigated targets: {', '.join(intent.target_files or intent.target_symbols or ['general'])}",
                    evidence_ids=[],
                    confidence=1.0,
                )
            ]
            code_changes = [
                {
                    "file_path": tf,
                    "symbol_name": intent.target_symbols[0] if intent.target_symbols else None,
                    "action": "modify",
                    "description": f"Implement proposed change: {intent.raw_query}",
                    "signature_or_snippet": None,
                    "affected_callers": [],
                }
                for tf in (intent.target_files or ["app/main.py"])
            ]
            return summary, claims, {"prompt_tokens": 0, "completion_tokens": 0}, code_changes

        sys_prompt, user_msg = build_reasoner_prompt(
            intent=intent,
            gathered_context=gathered_context,
            signals=signals,
            evidence_catalog=evidence_catalog or [],
        )

        try:
            async with httpx.AsyncClient(timeout=40.0) as client:
                data = await self._post_chat_completion(
                    client,
                    [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": user_msg},
                    ],
                )
                raw_text = data["choices"][0]["message"]["content"]
                cleaned_json = extract_json_payload(raw_text)
                output = ReasonerLLMOutput.model_validate_json(cleaned_json)

                usage = data.get("usage", {})
                tokens = {
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                }

                claims: List[InvestigationClaim] = []
                for c in output.claims:
                    cls_val = c.classification.lower()
                    if cls_val in ("fact", "inference", "unknown"):
                        claim_cls = ClaimClassification(cls_val)
                    else:
                        claim_cls = ClaimClassification.INFERENCE

                    claims.append(
                        InvestigationClaim(
                            id=c.id,
                            classification=claim_cls,
                            statement=c.statement,
                            evidence_ids=c.evidence_ids,
                            confidence=c.confidence,
                        )
                    )

                code_changes: List[Dict[str, Any]] = []
                for ch in output.code_changes:
                    code_changes.append(
                        {
                            "file_path": ch.file_path,
                            "symbol_name": ch.symbol_name,
                            "action": ch.action.lower(),
                            "description": ch.description,
                            "signature_or_snippet": ch.signature_or_snippet,
                            "affected_callers": ch.affected_callers,
                        }
                    )

                if not code_changes and intent.target_files:
                    for tf in intent.target_files:
                        code_changes.append(
                            {
                                "file_path": tf,
                                "symbol_name": intent.target_symbols[0]
                                if intent.target_symbols
                                else None,
                                "action": "modify",
                                "description": f"Implement changes for: {intent.raw_query}",
                                "signature_or_snippet": None,
                                "affected_callers": [],
                            }
                        )

                return output.summary, claims, tokens, code_changes
        except Exception as e:
            logger.warning(f"OpenRouter reasoning call failed, using fallback: {e}")
            fallback_changes = [
                {
                    "file_path": tf,
                    "symbol_name": intent.target_symbols[0] if intent.target_symbols else None,
                    "action": "modify",
                    "description": f"Apply change: {intent.raw_query}",
                    "signature_or_snippet": None,
                    "affected_callers": [],
                }
                for tf in (intent.target_files or ["unknown"])
            ]
            return (
                f"Grounded analysis for {intent.raw_query}",
                [
                    InvestigationClaim(
                        id="claim-fallback-1",
                        classification=ClaimClassification.FACT,
                        statement=f"Change targets {intent.target_files}",
                        evidence_ids=[],
                        confidence=0.5,
                    )
                ],
                {"prompt_tokens": 0, "completion_tokens": 0},
                fallback_changes,
            )

    async def verify_claims(
        self, claims: List[InvestigationClaim], evidence_catalog: List[Dict[str, Any]]
    ) -> Tuple[List[InvestigationClaim], Dict[str, int]]:
        valid_ev_ids = {str(e.get("id") or e.get("source_id")) for e in evidence_catalog}
        verified: List[InvestigationClaim] = []
        for c in claims:
            grounded_citations = [eid for eid in c.evidence_ids if str(eid) in valid_ev_ids]
            verified.append(
                InvestigationClaim(
                    id=c.id,
                    classification=c.classification,
                    statement=c.statement,
                    evidence_ids=grounded_citations,
                    confidence=c.confidence
                    if grounded_citations or c.classification != ClaimClassification.FACT
                    else 0.5,
                )
            )
        return verified, {"prompt_tokens": 0, "completion_tokens": 0}


class OpenAILLMProvider(OpenRouterLLMProvider):
    """OpenAI compatibility subclass defaulting to OpenAI API base URL."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        super().__init__(
            api_key=api_key or settings.OPENAI_API_KEY,
            model=model or settings.OPENAI_MODEL,
            base_url="https://api.openai.com/v1",
        )

    @property
    def headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}


def get_default_llm_provider() -> LLMProvider:
    """Return configured LLM provider, prioritizing OpenRouter."""
    if settings.OPENROUTER_API_KEY:
        return OpenRouterLLMProvider()
    if settings.OPENAI_API_KEY:
        return OpenAILLMProvider()
    return OpenRouterLLMProvider()
