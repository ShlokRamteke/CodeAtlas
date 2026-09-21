from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.investigation import (
    ChangeDecomposer,
    CodeOwnershipAnalyzer,
    IntentNormalizer,
    InvestigationEngine,
)
from app.investigation.concurrent_overlap import ConcurrentOverlapDetector
from app.investigation.distillation import GLOBAL_OMISSION_REGISTRY, TokenBudgetDistiller
from app.models.dependency import CodeDependency
from app.models.investigation import Investigation
from app.models.repository import Repository
from app.schemas.investigation import (
    ChangeDecompositionReportSchema,
    CodeOwnershipReportSchema,
    ConcurrentOverlapReportSchema,
    InvestigationCreate,
    InvestigationProjectionResponse,
    InvestigationRead,
    InvestigationRunRequest,
    NormalizedChangeIntentSchema,
    OmissionMarkerSchema,
    ReferenceDetailResponse,
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


def _reconstruct_brief_data(inv: Investigation) -> dict:
    target_files: list[str] = []
    target_symbols: list[str] = []
    signals: dict = {}
    constraints: list[dict] = []
    evidence_list: list[dict] = []
    recommended_checks: list[str] = []
    unknowns: list[str] = []
    code_changes: list[dict] = []

    for e in inv.evidence:
        ev_item = {
            "id": str(e.id),
            "source_type": (
                e.source_type.value if hasattr(e.source_type, "value") else str(e.source_type)
            ),
            "source_id": e.source_id,
            "title": e.title,
            "snippet": e.snippet,
            "path": e.path,
            "extra_metadata": e.extra_metadata or {},
        }
        evidence_list.append(ev_item)

        meta = e.extra_metadata or {}
        if e.source_id == "kamei-change-risk":
            signals["change_risk"] = meta
        elif e.source_id == "guarding-tests-report":
            signals["guarding_tests"] = meta
        elif e.source_id == "blast-radius-analysis":
            signals["blast_radius"] = meta
        elif e.source_id == "co-change-signals":
            signals["co_change"] = meta
        elif e.source_id in ("concurrent-branch-overlap", "concurrent-branch-overlap-report"):
            signals["concurrent_overlaps"] = meta
        elif e.source_id in ("change-decomposition", "change-decomposition-report"):
            signals["decomposition"] = meta
        elif e.source_id in ("code-ownership", "code-ownership-report"):
            signals["ownership"] = meta
        elif e.source_id.startswith("inv-") or meta.get("governing_status"):
            constraints.append(
                {
                    "id": meta.get("id", e.source_id),
                    "title": meta.get("title", e.title),
                    "statement": meta.get("statement", e.snippet),
                    "level": meta.get("level", "must"),
                    "category": meta.get("category", "general"),
                    "governing_status": meta.get("governing_status", "governing"),
                    "superseded_by": meta.get("superseded_by"),
                    "source_doc_title": meta.get("source_doc_title", ""),
                    "source_doc_path": meta.get("source_doc_path", e.path or ""),
                    "rationale": meta.get("rationale", ""),
                }
            )

    for e in inv.evidence:
        if e.path and e.path not in target_files:
            target_files.append(e.path)
        meta = e.extra_metadata or {}
        if e.source_id == "proposed-code-changes" or "code_changes" in meta:
            code_changes.extend(meta.get("code_changes", []))

    if not target_files:
        if "blast_radius" in signals and signals["blast_radius"].get("target_files"):
            target_files.extend(signals["blast_radius"]["target_files"])
        elif "ownership" in signals and signals["ownership"].get("target_files"):
            target_files.extend(signals["ownership"]["target_files"])
        elif "decomposition" in signals and signals["decomposition"].get("target_files"):
            target_files.extend(signals["decomposition"]["target_files"])
        elif "change_risk" in signals and signals["change_risk"].get("kamei_metrics", {}).get("target_files"):
            target_files.extend(signals["change_risk"]["kamei_metrics"]["target_files"])

    guarding_sig = signals.get("guarding_tests", {})
    if guarding_sig.get("untested_files"):
        unknowns.append(f"Untested targets: {', '.join(guarding_sig['untested_files'])}")
    if guarding_sig.get("ranked_tests"):
        top_t = guarding_sig["ranked_tests"][0]
        recommended_checks.append(
            f"Execute high-reach guarding test suite '{top_t.get('test_file')}' first."
        )

    return {
        "summary": inv.summary or inv.query,
        "intent_summary": inv.answer or inv.query,
        "target_files": target_files,
        "target_symbols": target_symbols,
        "claims": inv.claims or [],
        "signals": signals,
        "constraints": constraints,
        "unknowns": unknowns,
        "recommended_checks": recommended_checks,
        "code_changes": code_changes,
        "evidence": evidence_list,
        "token_usage": inv.token_usage or {},
    }


@router.get(
    "/{investigation_id}/projection",
    response_model=InvestigationProjectionResponse,
)
async def get_investigation_projection(
    investigation_id: uuid.UUID,
    format: str = Query("json", description="'json' or 'markdown'"),
    token_budget: Optional[int] = Query(
        None, description="Optional token limit (e.g. 500, 1000, 2000, 4000)"
    ),
    db: AsyncSession = Depends(get_db),
) -> InvestigationProjectionResponse:
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

    brief_data = _reconstruct_brief_data(inv)
    fmt = "json" if format.lower() == "json" else "markdown"
    distilled = TokenBudgetDistiller.distill_brief(
        brief_data=brief_data,
        token_budget=token_budget,
        output_format=fmt,
    )

    omissions_schema = [
        OmissionMarkerSchema(
            ref_id=o.ref_id,
            marker_type=o.marker_type,
            title=o.title,
            summary=o.summary,
        )
        for o in distilled.omissions
    ]

    return InvestigationProjectionResponse(
        investigation_id=inv.id,
        format=distilled.format,
        token_budget=distilled.token_budget,
        estimated_tokens=distilled.estimated_tokens,
        is_distilled=distilled.is_distilled,
        shed_tier=distilled.shed_tier,
        omitted_count=distilled.omitted_count,
        omissions=omissions_schema,
        content_text=distilled.content_text,
        content_json=distilled.content_json,
    )


@router.get(
    "/{investigation_id}/reference",
    response_model=ReferenceDetailResponse,
)
@router.get(
    "/{investigation_id}/references/{ref_id:path}",
    response_model=ReferenceDetailResponse,
)
async def get_investigation_reference(
    investigation_id: uuid.UUID,
    ref_id: Optional[str] = None,
    ref: Optional[str] = Query(None, alias="ref_id"),
    db: AsyncSession = Depends(get_db),
) -> ReferenceDetailResponse:
    target_ref = ref_id or ref
    if not target_ref:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ref_id must be specified",
        )

    import urllib.parse

    decoded_ref = urllib.parse.unquote(target_ref).strip()

    # 1. First check in-memory registry (try direct, decoded, and with/without ref#)
    marker = (
        GLOBAL_OMISSION_REGISTRY.get(target_ref)
        or GLOBAL_OMISSION_REGISTRY.get(decoded_ref)
        or GLOBAL_OMISSION_REGISTRY.get(f"ref#{decoded_ref.replace('ref#', '')}")
    )
    if marker:
        return ReferenceDetailResponse(
            ref_id=marker.ref_id,
            marker_type=marker.marker_type,
            title=marker.title,
            summary=marker.summary,
            original_payload=marker.original_payload,
        )

    # 2. Fallback: inspect persisted investigation evidence
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

    clean_ref = ref_id.replace("ref#", "")
    for e in inv.evidence:
        if clean_ref in str(e.id) or clean_ref == e.source_id or clean_ref in e.source_id:
            src_val = e.source_type.value if hasattr(e.source_type, "value") else str(e.source_type)
            return ReferenceDetailResponse(
                ref_id=ref_id,
                marker_type="evidence",
                title=e.title,
                summary=e.snippet[:200],
                original_payload={
                    "id": str(e.id),
                    "source_id": e.source_id,
                    "source_type": src_val,
                    "title": e.title,
                    "snippet": e.snippet,
                    "path": e.path,
                    "confidence": e.confidence,
                    "extra_metadata": e.extra_metadata or {},
                },
            )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Reference '{ref_id}' not found",
    )


@router.get(
    "/{investigation_id}/concurrent-overlap",
    response_model=ConcurrentOverlapReportSchema,
)
async def get_investigation_concurrent_overlap(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ConcurrentOverlapReportSchema:
    """Retrieve concurrent branch overlap & merge conflict report for an investigation."""
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

    # 1. Check if overlap report was cached in evidence
    for e in inv.evidence:
        if e.source_id == "concurrent-branch-overlap" and e.extra_metadata:
            return ConcurrentOverlapReportSchema(**e.extra_metadata)

    # 2. Otherwise run detector live on target files
    brief_data = _reconstruct_brief_data(inv)
    target_files = brief_data.get("target_files", [])
    blast_files = brief_data.get("signals", {}).get("blast_radius", {}).get("transitive_files", [])
    detector = ConcurrentOverlapDetector()
    report = await detector.detect_overlaps(
        db=db,
        repository_id=inv.repository_id,
        target_files=target_files,
        blast_radius_files=blast_files,
    )
    return ConcurrentOverlapReportSchema(**report.to_dict())


@router.get(
    "/{investigation_id}/decomposition",
    response_model=ChangeDecompositionReportSchema,
)
async def get_investigation_decomposition(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ChangeDecompositionReportSchema:
    """Retrieve independent change decomposition & modular PR recommendations for an investigation."""
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

    # 1. Check if decomposition report was cached in evidence
    for e in inv.evidence:
        if e.source_id == "change-decomposition" and e.extra_metadata:
            return ChangeDecompositionReportSchema(**e.extra_metadata)

    # 2. Otherwise run decomposer live on target files and dependencies
    brief_data = _reconstruct_brief_data(inv)
    target_files = brief_data.get("target_files", [])

    dep_query = select(CodeDependency).where(CodeDependency.repository_id == inv.repository_id)
    dep_res = await db.execute(dep_query)
    db_deps = dep_res.scalars().all()
    static_edges = [(d.source_path, d.target_path) for d in db_deps]

    report = ChangeDecomposer.evaluate_subgraph(
        target_files=target_files,
        dependency_edges=static_edges,
    )
    return ChangeDecompositionReportSchema(**report.to_dict())


@router.get(
    "/{investigation_id}/ownership",
    response_model=CodeOwnershipReportSchema,
)
async def get_investigation_ownership(
    investigation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> CodeOwnershipReportSchema:
    """Retrieve code ownership concentration and reviewer recommendations for an investigation."""
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

    # 1. Check if ownership report was cached in evidence
    for e in inv.evidence:
        if e.source_id == "code-ownership" and e.extra_metadata:
            return CodeOwnershipReportSchema(**e.extra_metadata)

    # 2. Otherwise run analyzer live on target files and blast radius
    brief_data = _reconstruct_brief_data(inv)
    target_files = brief_data.get("target_files", [])
    blast_files = brief_data.get("signals", {}).get("blast_radius", {}).get("transitive_files", [])

    report = await CodeOwnershipAnalyzer.query_and_analyze(
        db=db,
        repository_id=inv.repository_id,
        target_files=target_files,
        blast_radius_files=blast_files,
    )
    return CodeOwnershipReportSchema(**report.to_dict())
