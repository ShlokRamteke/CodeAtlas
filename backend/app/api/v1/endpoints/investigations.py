from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.models.investigation import Investigation
from app.models.repository import Repository
from app.schemas.investigation import InvestigationCreate, InvestigationRead

router = APIRouter()


@router.get("/repository/{repository_id}", response_model=list[InvestigationRead])
async def list_repository_investigations(
    repository_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[Investigation]:
    query = (
        select(Investigation)
        .where(Investigation.repository_id == repository_id)
        .options(selectinload(Investigation.evidence))
        .order_by(Investigation.created_at.desc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("", response_model=InvestigationRead, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=InvestigationRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_investigation(

    inv_in: InvestigationCreate,
    db: AsyncSession = Depends(get_db),
) -> Investigation:
    repo = await db.get(Repository, inv_in.repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    investigation = Investigation(
        repository_id=inv_in.repository_id,
        query=inv_in.query,
        type=inv_in.type,
    )
    db.add(investigation)
    await db.commit()
    await db.refresh(investigation, attribute_names=["evidence"])
    return investigation


@router.get("/{investigation_id}", response_model=InvestigationRead)
async def get_investigation(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Investigation:
    query = (
        select(Investigation)
        .where(Investigation.id == investigation_id)
        .options(selectinload(Investigation.evidence))
    )
    result = await db.execute(query)
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found",
        )
    return inv
