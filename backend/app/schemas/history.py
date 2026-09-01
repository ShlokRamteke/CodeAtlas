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


class LinkedPullRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pr_number: int
    link_type: str = "references"
    raw_reference: Optional[str] = None
    confidence: float = 1.0
    title: Optional[str] = None
    state: Optional[str] = None
    author: Optional[str] = None
    merged_at: Optional[datetime] = None
    labels: List[str] = []
    html_url: Optional[str] = None


class LinkedIssueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    issue_number: int
    link_type: str = "references"
    raw_reference: Optional[str] = None
    confidence: float = 1.0
    title: Optional[str] = None
    state: Optional[str] = None
    author: Optional[str] = None
    closed_at: Optional[datetime] = None
    labels: List[str] = []
    html_url: Optional[str] = None


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
    linked_pull_requests: List[LinkedPullRequestRead] = []
    linked_issues: List[LinkedIssueRead] = []


class PullRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    number: int
    title: str
    body: Optional[str] = None
    state: str
    author: str
    merged_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    labels: List[str] = []
    html_url: Optional[str] = None
    created_at: datetime
    linked_issues: List[LinkedIssueRead] = []
    linked_commits: List[Dict[str, Any]] = []


class IssueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    number: int
    title: str
    body: Optional[str] = None
    state: str
    author: str
    closed_at: Optional[datetime] = None
    labels: List[str] = []
    html_url: Optional[str] = None
    created_at: datetime
    linked_pull_requests: List[LinkedPullRequestRead] = []
    linked_commits: List[Dict[str, Any]] = []


class HistoricalTraceItem(BaseModel):
    commit_hash: str
    author_name: str
    committed_at: str
    message: str
    change_type: str
    insertions: int
    deletions: int
    linked_pull_requests: List[Dict[str, Any]] = []
    linked_issues: List[Dict[str, Any]] = []


class HistoricalTraceResponse(BaseModel):
    file_path: str
    total_commits: int
    total_pull_requests: int
    total_issues: int
    trace_chain: List[HistoricalTraceItem]
    all_pull_requests: List[Dict[str, Any]] = []
    all_issues: List[Dict[str, Any]] = []


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


class IngestPullRequestsRequest(BaseModel):
    pull_requests: List[Dict[str, Any]]


class IngestPullRequestsResponse(BaseModel):
    repository_id: uuid.UUID
    indexed_count: int
    message: str


class IngestIssuesRequest(BaseModel):
    issues: List[Dict[str, Any]]


class IngestIssuesResponse(BaseModel):
    repository_id: uuid.UUID
    indexed_count: int
    message: str
