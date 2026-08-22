from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.repository import Repository
from app.schemas.repository import RepositoryCreate, RepositoryRead

router = APIRouter()


@router.get("/", response_model=list[RepositoryRead])
async def list_repositories(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[Repository]:
    query = select(Repository).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("/", response_model=RepositoryRead, status_code=status.HTTP_201_CREATED)
async def create_repository(
    repo_in: RepositoryCreate,
    db: AsyncSession = Depends(get_db),
) -> Repository:
    existing = await db.execute(
        select(Repository).where(Repository.full_name == repo_in.full_name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Repository '{repo_in.full_name}' already exists",
        )

    repo = Repository(
        owner=repo_in.owner,
        name=repo_in.name,
        full_name=repo_in.full_name,
        default_branch=repo_in.default_branch,
    )
    db.add(repo)
    await db.commit()
    await db.refresh(repo)
    return repo


@router.get("/{repository_id}", response_model=RepositoryRead)
async def get_repository(
    repository_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Repository:
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )
    return repo
