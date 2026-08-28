from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.history.git_indexer import GitHistoryIndexer
from app.models.commit import Commit
from app.models.commit_file_change import CommitFileChange
from app.models.repository import Repository
from app.schemas.history import (
    CommitRead,
    ComponentHistoryResponse,
    FileHistoryResponse,
    IngestCommitsRequest,
    IngestCommitsResponse,
)

router = APIRouter()


@router.get("/{repository_id}/commits", response_model=List[CommitRead])
async def list_repository_commits(
    repository_id: uuid.UUID,
    file_path: Optional[str] = Query(None, description="Filter commits touching specific file"),
    author: Optional[str] = Query(None, description="Filter commits by author name or email"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> List[CommitRead]:
    """List commits for a repository with optional file and author filters."""
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
    return [CommitRead.model_validate(c) for c in commits]


@router.get("/{repository_id}/commits/{commit_hash}", response_model=CommitRead)
async def get_commit_detail(
    repository_id: uuid.UUID,
    commit_hash: str,
    db: AsyncSession = Depends(get_db),
) -> CommitRead:
    """Get single commit details including changed files and diff stats."""
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
    return CommitRead.model_validate(commit)


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


@router.get("/{repository_id}/components/{component_path:path}/history", response_model=ComponentHistoryResponse)
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
