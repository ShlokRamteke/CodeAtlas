from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.investigation.intent import NormalizedChangeIntent


class InvestigationStep(str, enum.Enum):
    INTAKE = "intake"
    PLAN = "plan"
    GATHER = "gather"
    REASON = "reason"
    VERIFY = "verify"
    SYNTHESIZE = "synthesize"
    COMPLETED = "completed"
    FAILED = "failed"


class ClaimClassification(str, enum.Enum):
    FACT = "fact"
    INFERENCE = "inference"
    UNKNOWN = "unknown"


@dataclass
class InvestigationClaim:
    id: str
    classification: ClaimClassification
    statement: str
    evidence_ids: List[str] = field(default_factory=list)
    confidence: float = 1.0


@dataclass
class InvestigationPlan:
    steps: List[str] = field(default_factory=list)
    target_files: List[str] = field(default_factory=list)
    target_symbols: List[str] = field(default_factory=list)
    gather_tasks: List[str] = field(default_factory=list)
    reasoning_focus: str = ""


@dataclass
class PreChangeBrief:
    summary: str
    intent_summary: str
    target_files: List[str] = field(default_factory=list)
    target_symbols: List[str] = field(default_factory=list)
    claims: List[InvestigationClaim] = field(default_factory=list)
    signals: Dict[str, Any] = field(default_factory=dict)
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    unknowns: List[str] = field(default_factory=list)
    recommended_checks: List[str] = field(default_factory=list)
    model_calls_count: int = 0
    token_usage: Dict[str, int] = field(default_factory=dict)


@dataclass
class InvestigationState:
    investigation_id: uuid.UUID
    repository_id: uuid.UUID
    query: str
    diff: Optional[str] = None
    file_stats: Optional[List[Dict[str, Any]]] = None
    step: InvestigationStep = InvestigationStep.INTAKE
    intent: Optional[NormalizedChangeIntent] = None
    plan: Optional[InvestigationPlan] = None
    gathered_context: Dict[str, Any] = field(default_factory=dict)
    gathered_evidence: List[Dict[str, Any]] = field(default_factory=list)
    gathered_signals: Dict[str, Any] = field(default_factory=dict)
    claims: List[InvestigationClaim] = field(default_factory=list)
    brief: Optional[PreChangeBrief] = None
    model_calls_count: int = 0
    max_model_calls: int = 3
    token_usage: Dict[str, int] = field(
        default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    )
    errors: List[str] = field(default_factory=list)
    latency_ms: int = 0

    def record_model_call(self, prompt_tokens: int = 0, completion_tokens: int = 0) -> None:
        """Increment model call counter and enforce bounded execution limit."""
        if self.model_calls_count >= self.max_model_calls:
            raise RuntimeError(
                f"Bounded investigation limit exceeded: {self.model_calls_count}/{self.max_model_calls} calls"
            )
        self.model_calls_count += 1
        self.token_usage["prompt_tokens"] += prompt_tokens
        self.token_usage["completion_tokens"] += completion_tokens
        self.token_usage["total_tokens"] += prompt_tokens + completion_tokens

    @property
    def can_call_model(self) -> bool:
        return self.model_calls_count < self.max_model_calls
