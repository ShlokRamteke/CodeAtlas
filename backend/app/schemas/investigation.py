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


class InvestigationCreate(BaseModel):
    repository_id: uuid.UUID
    query: str
    type: InvestigationType = InvestigationType.UNDERSTAND
    target_path: Optional[str] = None
    target_symbol: Optional[str] = None


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
