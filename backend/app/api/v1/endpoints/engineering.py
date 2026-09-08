from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.history.engineering_indexer import EngineeringContextIndexer
from app.models.design_constraint import (
    ConstraintCategory,
    ConstraintLevel,
    DesignConstraint,
)
from app.models.engineering_doc import (
    ADRStatus,
    EngineeringDocType,
    EngineeringDocument,
)
from app.models.repository import Repository
from app.schemas.engineering import (
    ADRRead,
    DesignConstraintRead,
    EngineeringContextOverviewResponse,
    EngineeringDocumentDetail,
    EngineeringDocumentRead,
    EngineeringSearchResponse,
    IngestEngineeringDocsRequest,
    IngestEngineeringDocsResponse,
)

router = APIRouter()


async def _get_repo_or_404(repository_id: uuid.UUID, db: AsyncSession) -> Repository:
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repository_id} not found",
        )
    return repo


@router.get(
    "/{repository_id}/engineering/overview",
    response_model=EngineeringContextOverviewResponse,
    summary="Get engineering context overview, statistics, ADRs, and top constraints",
)
async def get_engineering_overview(
    repository_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> EngineeringContextOverviewResponse:
    await _get_repo_or_404(repository_id, db)
    indexer = EngineeringContextIndexer(db)

    # 1. Total docs & by type
    docs_stmt = (
        select(EngineeringDocument.doc_type, func.count(EngineeringDocument.id))
        .where(EngineeringDocument.repository_id == repository_id)
        .group_by(EngineeringDocument.doc_type)
    )
    doc_res = await db.execute(docs_stmt)
    docs_by_type = {
        row[0].value if hasattr(row[0], "value") else str(row[0]): row[1] for row in doc_res.all()
    }
    total_docs = sum(docs_by_type.values())

    # 2. Total constraints & by category
    c_stmt = (
        select(DesignConstraint.category, func.count(DesignConstraint.id))
        .where(DesignConstraint.repository_id == repository_id)
        .group_by(DesignConstraint.category)
    )
    c_res = await db.execute(c_stmt)
    constraints_by_cat = {
        row[0].value if hasattr(row[0], "value") else str(row[0]): row[1] for row in c_res.all()
    }
    total_constraints = sum(constraints_by_cat.values())

    # 3. ADRs
    adrs = await indexer.get_adrs(repository_id)
    adr_reads = [
        ADRRead(
            id=a.id,
            repository_id=a.repository_id,
            path=a.path,
            title=a.title,
            status=a.status.value,
            deciders=a.deciders,
            summary=a.summary,
            created_at=a.created_at,
            updated_at=a.updated_at,
        )
        for a in adrs
    ]

    # 4. Top constraints
    top_constraints_raw = await indexer.get_constraints(repository_id, limit=20)
    top_constraints = [
        DesignConstraintRead(
            id=c.id,
            repository_id=c.repository_id,
            document_id=c.document_id,
            category=c.category.value,
            level=c.level.value,
            title=c.title,
            statement=c.statement,
            source_path=c.source_path,
            line_start=c.line_start,
            line_end=c.line_end,
            confidence=c.confidence,
            extra_metadata=c.extra_metadata or {},
            created_at=c.created_at,
        )
        for c in top_constraints_raw
    ]

    return EngineeringContextOverviewResponse(
        repository_id=repository_id,
        total_docs=total_docs,
        total_adrs=len(adr_reads),
        total_constraints=total_constraints,
        docs_by_type=docs_by_type,
        constraints_by_category=constraints_by_cat,
        adrs=adr_reads,
        top_constraints=top_constraints,
    )


@router.get(
    "/{repository_id}/engineering/docs",
    response_model=List[EngineeringDocumentRead],
    summary="List engineering documents for a repository",
)
async def get_engineering_docs(
    repository_id: uuid.UUID,
    doc_type: Optional[str] = Query(
        None, description="Filter by document type (readme, architecture, adr, etc.)"
    ),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> List[EngineeringDocumentRead]:
    await _get_repo_or_404(repository_id, db)
    indexer = EngineeringContextIndexer(db)

    filter_type: Optional[EngineeringDocType] = None
    if doc_type:
        try:
            filter_type = EngineeringDocType(doc_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid doc_type: {doc_type}",
            ) from None

    docs = await indexer.get_docs(repository_id, doc_type=filter_type, limit=limit, offset=offset)
    return [
        EngineeringDocumentRead(
            id=d.id,
            repository_id=d.repository_id,
            path=d.path,
            doc_type=d.doc_type.value,
            title=d.title,
            format=d.format,
            content_hash=d.content_hash,
            status=d.status.value,
            deciders=d.deciders,
            summary=d.summary,
            extra_metadata=d.extra_metadata or {},
            created_at=d.created_at,
            updated_at=d.updated_at,
        )
        for d in docs
    ]


@router.get(
    "/{repository_id}/engineering/docs/{doc_id}",
    response_model=EngineeringDocumentDetail,
    summary="Get detailed engineering document with full content and extracted constraints",
)
async def get_engineering_doc_detail(
    repository_id: uuid.UUID,
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> EngineeringDocumentDetail:
    await _get_repo_or_404(repository_id, db)
    indexer = EngineeringContextIndexer(db)

    doc = await indexer.get_doc_by_id(repository_id, doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Engineering document {doc_id} not found",
        )

    # Fetch associated constraints
    c_stmt = (
        select(DesignConstraint)
        .where(DesignConstraint.document_id == doc.id)
        .order_by(DesignConstraint.line_start)
    )
    c_res = await db.execute(c_stmt)
    constraints = list(c_res.scalars().all())

    return EngineeringDocumentDetail(
        id=doc.id,
        repository_id=doc.repository_id,
        path=doc.path,
        doc_type=doc.doc_type.value,
        title=doc.title,
        format=doc.format,
        content_hash=doc.content_hash,
        status=doc.status.value,
        deciders=doc.deciders,
        summary=doc.summary,
        raw_content=doc.raw_content,
        extra_metadata=doc.extra_metadata or {},
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        constraints=[
            DesignConstraintRead(
                id=c.id,
                repository_id=c.repository_id,
                document_id=c.document_id,
                category=c.category.value,
                level=c.level.value,
                title=c.title,
                statement=c.statement,
                source_path=c.source_path,
                line_start=c.line_start,
                line_end=c.line_end,
                confidence=c.confidence,
                extra_metadata=c.extra_metadata or {},
                created_at=c.created_at,
            )
            for c in constraints
        ],
    )


@router.get(
    "/{repository_id}/engineering/adrs",
    response_model=List[ADRRead],
    summary="List Architecture Decision Records (ADRs)",
)
async def get_adrs(
    repository_id: uuid.UUID,
    adr_status: Optional[str] = Query(
        None, description="Filter by status (accepted, superseded, proposed, etc.)"
    ),
    db: AsyncSession = Depends(get_db),
) -> List[ADRRead]:
    await _get_repo_or_404(repository_id, db)
    indexer = EngineeringContextIndexer(db)

    filter_status: Optional[ADRStatus] = None
    if adr_status:
        try:
            filter_status = ADRStatus(adr_status.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid ADR status: {adr_status}",
            ) from None

    adrs = await indexer.get_adrs(repository_id, status=filter_status)
    return [
        ADRRead(
            id=a.id,
            repository_id=a.repository_id,
            path=a.path,
            title=a.title,
            status=a.status.value,
            deciders=a.deciders,
            summary=a.summary,
            created_at=a.created_at,
            updated_at=a.updated_at,
        )
        for a in adrs
    ]


@router.get(
    "/{repository_id}/engineering/constraints",
    response_model=List[DesignConstraintRead],
    summary="List extracted design constraints and architectural invariants",
)
async def get_design_constraints(
    repository_id: uuid.UUID,
    category: Optional[str] = Query(
        None,
        description="Category filter (security, performance, architecture, testing, data_integrity)",
    ),
    level: Optional[str] = Query(None, description="Level filter (must, should, must_not)"),
    source_path: Optional[str] = Query(None, description="Filter by source file path"),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> List[DesignConstraintRead]:
    await _get_repo_or_404(repository_id, db)
    indexer = EngineeringContextIndexer(db)

    filter_cat: Optional[ConstraintCategory] = None
    if category:
        try:
            filter_cat = ConstraintCategory(category.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid constraint category: {category}",
            ) from None

    filter_lvl: Optional[ConstraintLevel] = None
    if level:
        try:
            filter_lvl = ConstraintLevel(level.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid constraint level: {level}",
            ) from None

    constraints = await indexer.get_constraints(
        repository_id,
        category=filter_cat,
        level=filter_lvl,
        source_path=source_path,
        limit=limit,
    )
    return [
        DesignConstraintRead(
            id=c.id,
            repository_id=c.repository_id,
            document_id=c.document_id,
            category=c.category.value,
            level=c.level.value,
            title=c.title,
            statement=c.statement,
            source_path=c.source_path,
            line_start=c.line_start,
            line_end=c.line_end,
            confidence=c.confidence,
            extra_metadata=c.extra_metadata or {},
            created_at=c.created_at,
        )
        for c in constraints
    ]


@router.get(
    "/{repository_id}/engineering/search",
    response_model=EngineeringSearchResponse,
    summary="Deterministic keyword search across engineering documents and constraints",
)
async def search_engineering_context(
    repository_id: uuid.UUID,
    q: str = Query(..., min_length=1, description="Keyword search query"),
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> EngineeringSearchResponse:
    await _get_repo_or_404(repository_id, db)
    indexer = EngineeringContextIndexer(db)

    results = await indexer.search_engineering_context(repository_id, query=q, limit=limit)
    return EngineeringSearchResponse(
        repository_id=repository_id,
        query=q,
        total_matches=results["total_matches"],
        docs=results["docs"],
        constraints=results["constraints"],
    )


@router.post(
    "/{repository_id}/engineering/ingest",
    response_model=IngestEngineeringDocsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest and index a set of engineering documents for a repository",
)
async def ingest_engineering_docs(
    repository_id: uuid.UUID,
    payload: IngestEngineeringDocsRequest,
    db: AsyncSession = Depends(get_db),
) -> IngestEngineeringDocsResponse:
    await _get_repo_or_404(repository_id, db)
    indexer = EngineeringContextIndexer(db)

    docs = await indexer.index_repository_docs(repository_id, payload.files)

    # Count constraints created
    c_count_stmt = select(func.count(DesignConstraint.id)).where(
        DesignConstraint.repository_id == repository_id
    )
    c_res = await db.execute(c_count_stmt)
    total_c = c_res.scalar_one()

    return IngestEngineeringDocsResponse(
        repository_id=repository_id,
        indexed_doc_count=len(docs),
        total_constraints_count=total_c,
        message=f"Successfully indexed {len(docs)} engineering documents and {total_c} design constraints.",
    )
