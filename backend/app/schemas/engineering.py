from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class DesignConstraintRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    document_id: Optional[uuid.UUID] = None
    category: str
    level: str
    title: str
    statement: str
    source_path: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    confidence: float = 1.0
    extra_metadata: Dict[str, Any] = {}
    created_at: datetime


class EngineeringDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    path: str
    doc_type: str
    title: str
    format: str
    content_hash: str
    status: str
    deciders: Optional[str] = None
    summary: Optional[str] = None
    extra_metadata: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime


class EngineeringDocumentDetail(EngineeringDocumentRead):
    raw_content: str
    constraints: List[DesignConstraintRead] = []


class ADRRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    path: str
    title: str
    status: str
    deciders: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class EngineeringSearchResponse(BaseModel):
    repository_id: uuid.UUID
    query: str
    total_matches: int
    docs: List[Dict[str, Any]] = []
    constraints: List[Dict[str, Any]] = []


class IngestEngineeringDocsRequest(BaseModel):
    files: Dict[str, str]  # {relative_path: content}


class IngestEngineeringDocsResponse(BaseModel):
    repository_id: uuid.UUID
    indexed_doc_count: int
    total_constraints_count: int
    message: str


class EngineeringContextOverviewResponse(BaseModel):
    repository_id: uuid.UUID
    total_docs: int
    total_adrs: int
    total_constraints: int
    docs_by_type: Dict[str, int] = {}
    constraints_by_category: Dict[str, int] = {}
    adrs: List[ADRRead] = []
    top_constraints: List[DesignConstraintRead] = []
