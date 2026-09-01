from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.dependency import DependencyKind
from app.models.repository import RepositoryStatus
from app.models.symbol import SymbolKind


class RepositoryBase(BaseModel):
    owner: str
    name: str
    full_name: str
    default_branch: str = "main"


class RepositoryCreate(RepositoryBase):
    pass


class RepositoryRead(RepositoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: RepositoryStatus
    indexed_at: Optional[datetime] = None
    file_count: int = 0
    symbol_count: int = 0
    commit_count: int = 0
    created_at: datetime
    updated_at: datetime


class SymbolRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    file_id: uuid.UUID
    repository_id: uuid.UUID
    name: str
    kind: SymbolKind
    line_start: int
    line_end: int
    signature: Optional[str] = None
    docstring: Optional[str] = None


class CodeDependencyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    source_file_id: uuid.UUID
    source_path: str
    target_path: str
    imported_symbol: Optional[str] = None
    kind: DependencyKind


class ComponentOverview(BaseModel):
    name: str
    path: str
    symbol_count: int
    file_count: int
    dependencies: List[str]
    tested_by: Optional[str] = None


class ComponentRelationshipSchema(BaseModel):
    source_name: str
    source_path: str
    target_name: str
    target_path: str
    type: str
    confidence: float = 1.0
    resolution_method: str = "tree_sitter_ast"


class ArchitectureOverviewResponse(BaseModel):
    repository_id: uuid.UUID
    file_count: int
    symbol_count: int
    dependency_count: int
    languages: Dict[str, int]
    major_components: List[ComponentOverview]
    relationships: List[ComponentRelationshipSchema]


class IngestFilesRequest(BaseModel):
    files: Dict[str, str]


class ConnectGitHubRequest(BaseModel):
    url_or_slug: str



class ConnectGitHubResponse(BaseModel):
    repository: RepositoryRead
    architecture: ArchitectureOverviewResponse


class ContextEntitySchema(BaseModel):
    id: str
    name: str
    kind: str
    path: str
    language: Optional[str] = None
    signature: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None


class ContextRelationshipSchema(BaseModel):
    source_name: str
    source_path: str
    target_name: str
    target_path: str
    type: str
    confidence: float = 1.0
    resolution_method: str = "tree_sitter_ast"


class ContextEvidenceSchema(BaseModel):
    id: str
    source_path: str
    kind: str
    content: str
    confidence: float = 1.0
    provenance: str = "tree_sitter_ast"


class ContextUnknownSchema(BaseModel):
    kind: str
    target: str
    description: str
    severity: str = "medium"


class ProjectContextRead(BaseModel):
    target_type: str
    target_id: str
    target_name: str
    summary: str
    confidence: float = 1.0
    provenance: str = "tree_sitter_ast"
    entities: List[ContextEntitySchema]
    relationships: List[ContextRelationshipSchema]
    evidence: List[ContextEvidenceSchema]
    unknowns: List[ContextUnknownSchema]
    human_markdown: str
    llm_prompt_context: str


# Backwards compatibility alias for Phase 2 ContextBrief
class ComponentBriefSchema(BaseModel):
    name: str
    path: str
    language: str
    symbol_count: int
    symbols: List[Dict[str, str]]
    dependencies: List[Dict[str, str]]
    callers: List[Dict[str, str]]
    tests: List[str]
    human_summary: str
    llm_context: str


class ContextBriefResponse(BaseModel):
    repository_id: uuid.UUID
    full_name: str
    file_count: int
    symbol_count: int
    dependency_count: int
    languages: Dict[str, int]
    components: List[ComponentBriefSchema]
    human_summary: str
    llm_context: str
    project_context: Optional[ProjectContextRead] = None



