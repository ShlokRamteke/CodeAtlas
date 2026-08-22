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
