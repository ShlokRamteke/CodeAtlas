from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.evidence import EvidenceSourceType
from app.models.investigation import InvestigationStatus, InvestigationType


class EvidenceItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_type: EvidenceSourceType
    source_id: str
    title: str
    snippet: str
    path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    confidence: float = 1.0
    extra_metadata: Dict[str, Any] = Field(default_factory=dict)


class InvestigationClaimSchema(BaseModel):
    id: str
    classification: str  # 'fact' | 'inference' | 'unknown'
    statement: str
    evidence_ids: List[str] = Field(default_factory=list)
    confidence: float = 1.0


class ReachableNodeSchema(BaseModel):
    path: str
    depth: int
    direction: str
    via: Optional[str] = None
    component: str = ""


class BlastRadiusResultSchema(BaseModel):
    target_files: List[str] = Field(default_factory=list)
    upstream_callers: List[ReachableNodeSchema] = Field(default_factory=list)
    downstream_dependencies: List[ReachableNodeSchema] = Field(default_factory=list)
    transitive_files: List[str] = Field(default_factory=list)
    affected_components: List[str] = Field(default_factory=list)
    max_depth_reached: int = 0
    total_affected_count: int = 0


class HiddenCouplingWarningSchema(BaseModel):
    target_file: str
    omitted_partner: str
    frequency: float
    co_change_count: int
    has_static_import: bool
    explanation: str


class NormalizedChangeIntentSchema(BaseModel):
    raw_query: str
    action_verbs: List[str] = Field(default_factory=list)
    target_files: List[str] = Field(default_factory=list)
    target_symbols: List[str] = Field(default_factory=list)
    target_components: List[str] = Field(default_factory=list)
    intent_summary: str = ""
    is_ambiguous: bool = False


class InvestigationPlanSchema(BaseModel):
    steps: List[str] = Field(default_factory=list)
    target_files: List[str] = Field(default_factory=list)
    target_symbols: List[str] = Field(default_factory=list)
    gather_tasks: List[str] = Field(default_factory=list)
    reasoning_focus: str = ""


class PreChangeBriefSchema(BaseModel):
    summary: str
    intent_summary: str
    target_files: List[str] = Field(default_factory=list)
    target_symbols: List[str] = Field(default_factory=list)
    claims: List[InvestigationClaimSchema] = Field(default_factory=list)
    signals: Dict[str, Any] = Field(default_factory=dict)
    constraints: List[Dict[str, Any]] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)
    recommended_checks: List[str] = Field(default_factory=list)
    model_calls_count: int = 0
    token_usage: Dict[str, int] = Field(default_factory=dict)


class KameiMetricsSchema(BaseModel):
    lines_added: int = 0
    lines_deleted: int = 0
    files_touched: int = 0
    distinct_directories: int = 0
    distinct_subsystems: int = 0
    shannon_entropy: float = 0.0


class ChangeRiskSchema(BaseModel):
    risk_score: float = 0.0
    risk_level: str = "LOW"
    kamei_metrics: KameiMetricsSchema = Field(default_factory=KameiMetricsSchema)
    defect_pressure: float = 0.0
    explanatory_factors: List[str] = Field(default_factory=list)
    fix_commit_count: int = 0


class ReachRankedTestSchema(BaseModel):
    test_file: str
    reached_target_count: int
    reached_targets: List[str] = Field(default_factory=list)


class UntestedChangeSchema(BaseModel):
    target_file: str
    explanation: str


class StaleTestCandidateSchema(BaseModel):
    target_file: str
    guarding_tests: List[str] = Field(default_factory=list)
    explanation: str


class GuardingTestReportSchema(BaseModel):
    ranked_tests: List[ReachRankedTestSchema] = Field(default_factory=list)
    untested_changes: List[UntestedChangeSchema] = Field(default_factory=list)
    stale_test_candidates: List[StaleTestCandidateSchema] = Field(default_factory=list)
    total_guarding_tests: int = 0
    has_coverage_gaps: bool = False
    untested_files: List[str] = Field(default_factory=list)



class InvestigationCreate(BaseModel):
    repository_id: uuid.UUID
    query: str
    type: InvestigationType = InvestigationType.UNDERSTAND
    target_path: Optional[str] = None
    target_symbol: Optional[str] = None
    diff: Optional[str] = None


class InvestigationRunRequest(BaseModel):
    target_path: Optional[str] = None
    target_symbol: Optional[str] = None
    diff: Optional[str] = None


class InvestigationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    query: str
    type: InvestigationType
    status: InvestigationStatus
    summary: Optional[str] = None
    answer: Optional[str] = None
    claims: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[EvidenceItemSchema] = Field(default_factory=list)
    token_usage: Optional[Dict[str, Any]] = None
    latency_ms: Optional[int] = None
    created_at: datetime
