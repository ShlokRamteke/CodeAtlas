from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class CommitFileChangeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    commit_id: uuid.UUID
    file_path: str
    change_type: str
    insertions: int
    deletions: int
    old_path: Optional[str] = None


class CommitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    commit_hash: str
    author_name: str
    author_email: str
    committed_at: datetime
    message: str
    files_changed_count: int
    insertions: int
    deletions: int
    file_changes: List[CommitFileChangeRead] = []


class FileHistoryResponse(BaseModel):
    file_path: str
    total_commits: int
    introducing_commit: Optional[Dict[str, Any]] = None
    commits: List[Dict[str, Any]]
    authors: List[Dict[str, Any]]


class ComponentHistoryResponse(BaseModel):
    component_path: str
    total_commits: int
    introducing_commit: Optional[Dict[str, Any]] = None
    commits: List[Dict[str, Any]]
    top_authors: List[Dict[str, Any]]
    files_touched: List[Dict[str, Any]]


class IngestCommitsRequest(BaseModel):
    commits: List[Dict[str, Any]]


class IngestCommitsResponse(BaseModel):
    repository_id: uuid.UUID
    indexed_count: int
    message: str
