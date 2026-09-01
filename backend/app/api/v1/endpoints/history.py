from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.history.git_indexer import GitHistoryIndexer
from app.history.historical_linker import HistoricalLinker
from app.models.commit import Commit
from app.models.commit_file_change import CommitFileChange
from app.models.issue import Issue
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.schemas.history import (
    CommitFileChangeRead,
    CommitRead,
    ComponentHistoryResponse,
    FileHistoryResponse,
    HistoricalTraceItem,
    HistoricalTraceResponse,
    IngestCommitsRequest,
    IngestCommitsResponse,
    IngestIssuesRequest,
    IngestIssuesResponse,
    IngestPullRequestsRequest,
    IngestPullRequestsResponse,
    IssueRead,
    LinkedIssueRead,
    LinkedPullRequestRead,
    PullRequestRead,
)

router = APIRouter()


async def _format_commit_read(commit: Commit, db: AsyncSession) -> CommitRead:
    """Format Commit with populated linked PRs and Issues."""
    # CommitFileChanges
    changes_read = [
        CommitFileChangeRead.model_validate(fc) for fc in getattr(commit, "file_changes", [])
    ]

    # Linked PRs
    linked_prs: List[LinkedPullRequestRead] = []
    for pl in getattr(commit, "pull_request_links", []):
        pr_obj: Optional[PullRequest] = None
        if pl.pull_request_id:
            pr_obj = await db.get(PullRequest, pl.pull_request_id)
        elif pl.pr_number:
            stmt = select(PullRequest).where(
                PullRequest.repository_id == commit.repository_id,
                PullRequest.number == pl.pr_number,
            )
            pr_obj = (await db.execute(stmt)).scalar_one_or_none()

        linked_prs.append(
            LinkedPullRequestRead(
                pr_number=pl.pr_number,
                link_type=pl.link_type,
                raw_reference=pl.raw_reference,
                confidence=pl.confidence,
                title=pr_obj.title if pr_obj else None,
                state=pr_obj.state.value if pr_obj else None,
                author=pr_obj.author if pr_obj else None,
                merged_at=pr_obj.merged_at if pr_obj else None,
                labels=pr_obj.labels if pr_obj and pr_obj.labels else [],
                html_url=pr_obj.html_url if pr_obj else None,
            )
        )

    # Linked Issues
    linked_issues: List[LinkedIssueRead] = []
    for il in getattr(commit, "issue_links", []):
        iss_obj: Optional[Issue] = None
        if il.issue_id:
            iss_obj = await db.get(Issue, il.issue_id)
        elif il.issue_number:
            stmt = select(Issue).where(
                Issue.repository_id == commit.repository_id,
                Issue.number == il.issue_number,
            )
            iss_obj = (await db.execute(stmt)).scalar_one_or_none()

        linked_issues.append(
            LinkedIssueRead(
                issue_number=il.issue_number,
                link_type=il.link_type,
                raw_reference=il.raw_reference,
                confidence=il.confidence,
                title=iss_obj.title if iss_obj else None,
                state=iss_obj.state.value if iss_obj else None,
                author=iss_obj.author if iss_obj else None,
                closed_at=iss_obj.closed_at if iss_obj else None,
                labels=iss_obj.labels if iss_obj and iss_obj.labels else [],
                html_url=iss_obj.html_url if iss_obj else None,
            )
        )

    return CommitRead(
        id=commit.id,
        repository_id=commit.repository_id,
        commit_hash=commit.commit_hash,
        author_name=commit.author_name,
        author_email=commit.author_email,
        committed_at=commit.committed_at,
        message=commit.message,
        files_changed_count=commit.files_changed_count,
        insertions=commit.insertions,
        deletions=commit.deletions,
        file_changes=changes_read,
        linked_pull_requests=linked_prs,
        linked_issues=linked_issues,
    )


# --- Commits Endpoints ---


@router.get("/{repository_id}/commits", response_model=List[CommitRead])
async def list_repository_commits(
    repository_id: uuid.UUID,
    file_path: Optional[str] = Query(None, description="Filter commits touching specific file"),
    author: Optional[str] = Query(None, description="Filter commits by author name or email"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> List[CommitRead]:
    """List commits for a repository with optional file and author filters, including PR & Issue links."""
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    if file_path:
        stmt = (
            select(Commit)
            .join(CommitFileChange, Commit.id == CommitFileChange.commit_id)
            .where(
                Commit.repository_id == repository_id,
                CommitFileChange.file_path == file_path,
            )
            .order_by(Commit.committed_at.desc())
            .offset(offset)
            .limit(limit)
        )
    else:
        stmt = select(Commit).where(Commit.repository_id == repository_id)
        if author:
            stmt = stmt.where(
                (Commit.author_name.ilike(f"%{author}%"))
                | (Commit.author_email.ilike(f"%{author}%"))
            )
        stmt = stmt.order_by(Commit.committed_at.desc()).offset(offset).limit(limit)

    commits = list((await db.execute(stmt)).scalars().all())
    return [await _format_commit_read(c, db) for c in commits]


@router.get("/{repository_id}/commits/{commit_hash}", response_model=CommitRead)
async def get_commit_detail(
    repository_id: uuid.UUID,
    commit_hash: str,
    db: AsyncSession = Depends(get_db),
) -> CommitRead:
    """Get single commit details including changed files and linked PRs & Issues."""
    stmt = select(Commit).where(
        Commit.repository_id == repository_id,
        Commit.commit_hash == commit_hash,
    )
    commit = (await db.execute(stmt)).scalar_one_or_none()
    if not commit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Commit '{commit_hash}' not found",
        )
    return await _format_commit_read(commit, db)


@router.get("/{repository_id}/files/{file_path:path}/history", response_model=FileHistoryResponse)
async def get_file_history(
    repository_id: uuid.UUID,
    file_path: str,
    db: AsyncSession = Depends(get_db),
) -> FileHistoryResponse:
    """Retrieve chronological history for a file and identify its introducing commit."""
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    indexer = GitHistoryIndexer()
    result = await indexer.get_file_history(repository_id, file_path, db)
    return FileHistoryResponse(
        file_path=result.file_path,
        total_commits=result.total_commits,
        introducing_commit=result.introducing_commit,
        commits=result.commits,
        authors=result.authors,
    )


@router.get(
    "/{repository_id}/components/{component_path:path}/history",
    response_model=ComponentHistoryResponse,
)
async def get_component_history(
    repository_id: uuid.UUID,
    component_path: str,
    db: AsyncSession = Depends(get_db),
) -> ComponentHistoryResponse:
    """Retrieve aggregated historical changes for a component."""
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    indexer = GitHistoryIndexer()
    result = await indexer.get_component_history(repository_id, component_path, db)
    return ComponentHistoryResponse(
        component_path=result["component_path"],
        total_commits=result["total_commits"],
        introducing_commit=result["introducing_commit"],
        commits=result["commits"],
        top_authors=result["top_authors"],
        files_touched=result["files_touched"],
    )


@router.post("/{repository_id}/commits/ingest", response_model=IngestCommitsResponse)
async def ingest_repository_commits(
    repository_id: uuid.UUID,
    payload: IngestCommitsRequest,
    db: AsyncSession = Depends(get_db),
) -> IngestCommitsResponse:
    """Ingest structured commit history payload for a repository."""
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    indexer = GitHistoryIndexer()
    parsed_commits = indexer.parse_synthetic_payload(payload.commits)
    indexed_count = await indexer.index_commits(repository_id, parsed_commits, db)

    return IngestCommitsResponse(
        repository_id=repository_id,
        indexed_count=indexed_count,
        message=f"Successfully indexed {indexed_count} commits.",
    )


# --- Pull Requests Endpoints ---


@router.get("/{repository_id}/pull-requests", response_model=List[PullRequestRead])
async def list_repository_pull_requests(
    repository_id: uuid.UUID,
    state: Optional[str] = Query(None, description="Filter by state (open, closed, merged)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> List[PullRequestRead]:
    """List pull requests for a repository with linked issues and resolving commits."""
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    stmt = select(PullRequest).where(PullRequest.repository_id == repository_id)
    if state:
        stmt = stmt.where(PullRequest.state == state.lower())
    stmt = stmt.order_by(PullRequest.number.desc()).offset(offset).limit(limit)
    prs = list((await db.execute(stmt)).scalars().all())

    results: List[PullRequestRead] = []
    for pr in prs:
        # Linked issues
        issue_links: List[LinkedIssueRead] = []
        for pil in getattr(pr, "issue_links", []):
            iss_obj = await db.get(Issue, pil.issue_id) if pil.issue_id else None
            issue_links.append(
                LinkedIssueRead(
                    issue_number=pil.issue_number,
                    link_type=pil.link_type,
                    raw_reference=pil.raw_reference,
                    confidence=pil.confidence,
                    title=iss_obj.title if iss_obj else None,
                    state=iss_obj.state.value if iss_obj else None,
                    author=iss_obj.author if iss_obj else None,
                    closed_at=iss_obj.closed_at if iss_obj else None,
                    labels=iss_obj.labels if iss_obj and iss_obj.labels else [],
                    html_url=iss_obj.html_url if iss_obj else None,
                )
            )

        # Linked commits
        commit_links_data: List[Dict[str, Any]] = []
        for cl in getattr(pr, "commit_links", []):
            c_obj = await db.get(Commit, cl.commit_id) if cl.commit_id else None
            if c_obj:
                commit_links_data.append(
                    {
                        "commit_hash": c_obj.commit_hash,
                        "message": c_obj.message,
                        "author_name": c_obj.author_name,
                        "committed_at": c_obj.committed_at.isoformat(),
                        "link_type": cl.link_type,
                    }
                )

        results.append(
            PullRequestRead(
                id=pr.id,
                repository_id=pr.repository_id,
                number=pr.number,
                title=pr.title,
                body=pr.body,
                state=pr.state.value,
                author=pr.author,
                merged_at=pr.merged_at,
                closed_at=pr.closed_at,
                labels=pr.labels or [],
                html_url=pr.html_url,
                created_at=pr.created_at,
                linked_issues=issue_links,
                linked_commits=commit_links_data,
            )
        )

    return results


@router.get("/{repository_id}/pull-requests/{number}", response_model=PullRequestRead)
async def get_pull_request_detail(
    repository_id: uuid.UUID,
    number: int,
    db: AsyncSession = Depends(get_db),
) -> PullRequestRead:
    """Get single pull request details with linked issues and commits."""
    stmt = select(PullRequest).where(
        PullRequest.repository_id == repository_id,
        PullRequest.number == number,
    )
    pr = (await db.execute(stmt)).scalar_one_or_none()
    if not pr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pull request #{number} not found",
        )

    # Linked issues
    issue_links: List[LinkedIssueRead] = []
    for pil in getattr(pr, "issue_links", []):
        iss_obj = await db.get(Issue, pil.issue_id) if pil.issue_id else None
        issue_links.append(
            LinkedIssueRead(
                issue_number=pil.issue_number,
                link_type=pil.link_type,
                raw_reference=pil.raw_reference,
                confidence=pil.confidence,
                title=iss_obj.title if iss_obj else None,
                state=iss_obj.state.value if iss_obj else None,
                author=iss_obj.author if iss_obj else None,
                closed_at=iss_obj.closed_at if iss_obj else None,
                labels=iss_obj.labels if iss_obj and iss_obj.labels else [],
                html_url=iss_obj.html_url if iss_obj else None,
            )
        )

    # Linked commits
    commit_links_data: List[Dict[str, Any]] = []
    for cl in getattr(pr, "commit_links", []):
        c_obj = await db.get(Commit, cl.commit_id) if cl.commit_id else None
        if c_obj:
            commit_links_data.append(
                {
                    "commit_hash": c_obj.commit_hash,
                    "message": c_obj.message,
                    "author_name": c_obj.author_name,
                    "committed_at": c_obj.committed_at.isoformat(),
                    "link_type": cl.link_type,
                }
            )

    return PullRequestRead(
        id=pr.id,
        repository_id=pr.repository_id,
        number=pr.number,
        title=pr.title,
        body=pr.body,
        state=pr.state.value,
        author=pr.author,
        merged_at=pr.merged_at,
        closed_at=pr.closed_at,
        labels=pr.labels or [],
        html_url=pr.html_url,
        created_at=pr.created_at,
        linked_issues=issue_links,
        linked_commits=commit_links_data,
    )


@router.post("/{repository_id}/pull-requests/ingest", response_model=IngestPullRequestsResponse)
async def ingest_repository_pull_requests(
    repository_id: uuid.UUID,
    payload: IngestPullRequestsRequest,
    db: AsyncSession = Depends(get_db),
) -> IngestPullRequestsResponse:
    """Ingest structured pull request payload for a repository."""
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    linker = HistoricalLinker()
    parsed_prs = linker.parse_synthetic_prs(payload.pull_requests)
    indexed_count = await linker.index_pull_requests(repository_id, parsed_prs, db)

    return IngestPullRequestsResponse(
        repository_id=repository_id,
        indexed_count=indexed_count,
        message=f"Successfully indexed {indexed_count} pull requests.",
    )


# --- Issues Endpoints ---


@router.get("/{repository_id}/issues", response_model=List[IssueRead])
async def list_repository_issues(
    repository_id: uuid.UUID,
    state: Optional[str] = Query(None, description="Filter by state (open, closed)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> List[IssueRead]:
    """List issues for a repository with linked pull requests and commits."""
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    stmt = select(Issue).where(Issue.repository_id == repository_id)
    if state:
        stmt = stmt.where(Issue.state == state.lower())
    stmt = stmt.order_by(Issue.number.desc()).offset(offset).limit(limit)
    issues = list((await db.execute(stmt)).scalars().all())

    results: List[IssueRead] = []
    for issue in issues:
        # Linked PRs
        pr_links_data: List[LinkedPullRequestRead] = []
        for pil in getattr(issue, "pull_request_links", []):
            pr_obj = await db.get(PullRequest, pil.pull_request_id) if pil.pull_request_id else None
            if pr_obj:
                pr_links_data.append(
                    LinkedPullRequestRead(
                        pr_number=pr_obj.number,
                        link_type=pil.link_type,
                        raw_reference=pil.raw_reference,
                        confidence=pil.confidence,
                        title=pr_obj.title,
                        state=pr_obj.state.value,
                        author=pr_obj.author,
                        merged_at=pr_obj.merged_at,
                        labels=pr_obj.labels or [],
                        html_url=pr_obj.html_url,
                    )
                )

        # Linked commits
        commit_links_data: List[Dict[str, Any]] = []
        for cl in getattr(issue, "commit_links", []):
            c_obj = await db.get(Commit, cl.commit_id) if cl.commit_id else None
            if c_obj:
                commit_links_data.append(
                    {
                        "commit_hash": c_obj.commit_hash,
                        "message": c_obj.message,
                        "author_name": c_obj.author_name,
                        "committed_at": c_obj.committed_at.isoformat(),
                        "link_type": cl.link_type,
                    }
                )

        results.append(
            IssueRead(
                id=issue.id,
                repository_id=issue.repository_id,
                number=issue.number,
                title=issue.title,
                body=issue.body,
                state=issue.state.value,
                author=issue.author,
                closed_at=issue.closed_at,
                labels=issue.labels or [],
                html_url=issue.html_url,
                created_at=issue.created_at,
                linked_pull_requests=pr_links_data,
                linked_commits=commit_links_data,
            )
        )

    return results


@router.get("/{repository_id}/issues/{number}", response_model=IssueRead)
async def get_issue_detail(
    repository_id: uuid.UUID,
    number: int,
    db: AsyncSession = Depends(get_db),
) -> IssueRead:
    """Get single issue details with linked pull requests and commits."""
    stmt = select(Issue).where(
        Issue.repository_id == repository_id,
        Issue.number == number,
    )
    issue = (await db.execute(stmt)).scalar_one_or_none()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issue #{number} not found",
        )

    pr_links_data: List[LinkedPullRequestRead] = []
    for pil in getattr(issue, "pull_request_links", []):
        pr_obj = await db.get(PullRequest, pil.pull_request_id) if pil.pull_request_id else None
        if pr_obj:
            pr_links_data.append(
                LinkedPullRequestRead(
                    pr_number=pr_obj.number,
                    link_type=pil.link_type,
                    raw_reference=pil.raw_reference,
                    confidence=pil.confidence,
                    title=pr_obj.title,
                    state=pr_obj.state.value,
                    author=pr_obj.author,
                    merged_at=pr_obj.merged_at,
                    labels=pr_obj.labels or [],
                    html_url=pr_obj.html_url,
                )
            )

    commit_links_data: List[Dict[str, Any]] = []
    for cl in getattr(issue, "commit_links", []):
        c_obj = await db.get(Commit, cl.commit_id) if cl.commit_id else None
        if c_obj:
            commit_links_data.append(
                {
                    "commit_hash": c_obj.commit_hash,
                    "message": c_obj.message,
                    "author_name": c_obj.author_name,
                    "committed_at": c_obj.committed_at.isoformat(),
                    "link_type": cl.link_type,
                }
            )

    return IssueRead(
        id=issue.id,
        repository_id=issue.repository_id,
        number=issue.number,
        title=issue.title,
        body=issue.body,
        state=issue.state.value,
        author=issue.author,
        closed_at=issue.closed_at,
        labels=issue.labels or [],
        html_url=issue.html_url,
        created_at=issue.created_at,
        linked_pull_requests=pr_links_data,
        linked_commits=commit_links_data,
    )


@router.post("/{repository_id}/issues/ingest", response_model=IngestIssuesResponse)
async def ingest_repository_issues(
    repository_id: uuid.UUID,
    payload: IngestIssuesRequest,
    db: AsyncSession = Depends(get_db),
) -> IngestIssuesResponse:
    """Ingest structured issues payload for a repository."""
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    linker = HistoricalLinker()
    parsed_issues = linker.parse_synthetic_issues(payload.issues)
    indexed_count = await linker.index_issues(repository_id, parsed_issues, db)

    return IngestIssuesResponse(
        repository_id=repository_id,
        indexed_count=indexed_count,
        message=f"Successfully indexed {indexed_count} issues.",
    )


# --- Provenance Trace Endpoint ---


@router.get("/{repository_id}/trace/{file_path:path}", response_model=HistoricalTraceResponse)
async def get_historical_trace(
    repository_id: uuid.UUID,
    file_path: str,
    db: AsyncSession = Depends(get_db),
) -> HistoricalTraceResponse:
    """
    Traces the entire historical chain for a file or component:
    Code / File -> Commit -> Pull Request -> Issue.
    """
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    linker = HistoricalLinker()
    result = await linker.get_historical_trace(repository_id, file_path, db)

    trace_items = [
        HistoricalTraceItem(
            commit_hash=item["commit_hash"],
            author_name=item["author_name"],
            committed_at=item["committed_at"],
            message=item["message"],
            change_type=item["change_type"],
            insertions=item["insertions"],
            deletions=item["deletions"],
            linked_pull_requests=item["linked_pull_requests"],
            linked_issues=item["linked_issues"],
        )
        for item in result["trace_chain"]
    ]

    return HistoricalTraceResponse(
        file_path=result["file_path"],
        total_commits=result["total_commits"],
        total_pull_requests=result["total_pull_requests"],
        total_issues=result["total_issues"],
        trace_chain=trace_items,
        all_pull_requests=result["all_pull_requests"],
        all_issues=result["all_issues"],
    )
