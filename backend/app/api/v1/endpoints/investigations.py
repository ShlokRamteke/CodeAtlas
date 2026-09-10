from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.investigation import IntentNormalizer, InvestigationEngine
from app.models.investigation import Investigation
from app.models.repository import Repository
from app.schemas.investigation import (
    InvestigationCreate,
    InvestigationRead,
    InvestigationRunRequest,
    NormalizedChangeIntentSchema,
)

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
@router.post(
    "/",
    response_model=InvestigationRead,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
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


@router.post("/preview-intent", response_model=NormalizedChangeIntentSchema)
async def preview_intent(
    query: str,
    target_path: Optional[str] = None,
    target_symbol: Optional[str] = None,
) -> NormalizedChangeIntentSchema:
    intent = IntentNormalizer.normalize(
        raw_query=query,
        target_path=target_path,
        target_symbol=target_symbol,
    )
    return NormalizedChangeIntentSchema(
        raw_query=intent.raw_query,
        action_verbs=intent.action_verbs,
        target_files=intent.target_files,
        target_symbols=intent.target_symbols,
        target_components=intent.target_components,
        intent_summary=intent.intent_summary,
        is_ambiguous=intent.is_ambiguous,
    )


@router.post("/{investigation_id}/run", response_model=InvestigationRead)
async def run_investigation(
    investigation_id: uuid.UUID,
    run_req: Optional[InvestigationRunRequest] = None,
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

    engine = InvestigationEngine()
    target_path = run_req.target_path if run_req else None
    target_symbol = run_req.target_symbol if run_req else None
    diff = run_req.diff if run_req else None

    await engine.run(
        investigation_id=inv.id,
        db=db,
        target_path=target_path,
        target_symbol=target_symbol,
        diff=diff,
    )

    # Refresh with evidence
    result = await db.execute(query)
    updated_inv = result.scalar_one()
    return updated_inv
