from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.ingestion.engine import IngestionEngine
from app.ingestion.github_fetcher import GitHubRepoFetcher
from app.models.dependency import CodeDependency
from app.models.repository import Repository
from app.models.source_file import SourceFile
from app.models.symbol import Symbol, SymbolKind
from app.parser.ast_parser import ExtractedDependency, ExtractedSymbol, ParsedFileResult
from app.parser.relationship_analyzer import RelationshipAnalyzer
from app.schemas.repository import (
    ArchitectureOverviewResponse,
    CodeDependencyRead,
    ComponentOverview,
    ComponentRelationshipSchema,
    ConnectGitHubRequest,
    ConnectGitHubResponse,
    IngestFilesRequest,
    RepositoryCreate,
    RepositoryRead,
    SymbolRead,
)

router = APIRouter()


@router.post("/connect-github", response_model=ConnectGitHubResponse)
async def connect_and_ingest_github_repo(
    payload: ConnectGitHubRequest,
    db: AsyncSession = Depends(get_db),
) -> ConnectGitHubResponse:
    fetcher = GitHubRepoFetcher()
    try:
        owner, name = fetcher.parse_repo_url(payload.url_or_slug)
        full_name = f"{owner}/{name}"

        # 1. Fetch files from GitHub
        files, default_branch = await fetcher.fetch_public_repo_files(
            owner=owner,
            repo=name,
            github_token=payload.github_token,
        )

        if not files:
            raise ValueError(f"No supported code files found in repository '{full_name}'.")

        # 2. Get or create Repository
        stmt = select(Repository).where(Repository.full_name == full_name)
        repo = (await db.execute(stmt)).scalar_one_or_none()
        if not repo:
            repo = Repository(
                owner=owner,
                name=name,
                full_name=full_name,
                default_branch=default_branch,
            )
            db.add(repo)
            await db.commit()
            await db.refresh(repo)

        # 3. Ingest files with Tree-sitter
        engine = IngestionEngine(db)
        arch = await engine.ingest_files(repo.id, files)

        # 4. Refresh repo
        await db.refresh(repo)

        return ConnectGitHubResponse(
            repository=RepositoryRead.model_validate(repo),
            architecture=ArchitectureOverviewResponse(
                repository_id=repo.id,
                file_count=arch.file_count,
                symbol_count=arch.symbol_count,
                dependency_count=arch.dependency_count,
                languages=arch.languages,
                major_components=[
                    ComponentOverview(
                        name=c.name,
                        path=c.path,
                        symbol_count=c.symbol_count,
                        file_count=c.file_count,
                        dependencies=c.dependencies,
                        tested_by=c.tested_by,
                    )
                    for c in arch.major_components
                ],
                relationships=[
                    ComponentRelationshipSchema(
                        source_name=r.source_name,
                        source_path=r.source_path,
                        target_name=r.target_name,
                        target_path=r.target_path,
                        type=r.type,
                    )
                    for r in arch.relationships
                ],
            ),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e



@router.get("", response_model=List[RepositoryRead])
@router.get("/", response_model=List[RepositoryRead], include_in_schema=False)
async def list_repositories(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> List[Repository]:
    stmt = select(Repository).offset(skip).limit(limit).order_by(Repository.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=RepositoryRead, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=RepositoryRead, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_repository(
    payload: RepositoryCreate,
    db: AsyncSession = Depends(get_db),
) -> Repository:

    stmt = select(Repository).where(Repository.full_name == payload.full_name)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Repository '{payload.full_name}' already exists.",
        )

    repo = Repository(
        owner=payload.owner,
        name=payload.name,
        full_name=payload.full_name,
        default_branch=payload.default_branch,
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
    stmt = select(Repository).where(Repository.id == repository_id)
    repo = (await db.execute(stmt)).scalar_one_or_none()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repository_id} not found.",
        )
    return repo


@router.post("/{repository_id}/ingest", response_model=ArchitectureOverviewResponse)
async def ingest_repository_files(
    repository_id: uuid.UUID,
    payload: IngestFilesRequest,
    db: AsyncSession = Depends(get_db),
) -> ArchitectureOverviewResponse:
    engine = IngestionEngine(db)
    try:
        arch = await engine.ingest_files(repository_id, payload.files)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


    return ArchitectureOverviewResponse(
        repository_id=repository_id,
        file_count=arch.file_count,
        symbol_count=arch.symbol_count,
        dependency_count=arch.dependency_count,
        languages=arch.languages,
        major_components=[
            ComponentOverview(
                name=c.name,
                path=c.path,
                symbol_count=c.symbol_count,
                file_count=c.file_count,
                dependencies=c.dependencies,
                tested_by=c.tested_by,
            )
            for c in arch.major_components
        ],
        relationships=[
            ComponentRelationshipSchema(
                source_name=r.source_name,
                source_path=r.source_path,
                target_name=r.target_name,
                target_path=r.target_path,
                type=r.type,
            )
            for r in arch.relationships
        ],
    )


@router.get("/{repository_id}/symbols", response_model=List[SymbolRead])
async def list_repository_symbols(
    repository_id: uuid.UUID,
    name: Optional[str] = Query(None, description="Search symbol by name"),
    kind: Optional[SymbolKind] = Query(None, description="Filter by symbol kind"),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> List[Symbol]:
    stmt = select(Symbol).where(Symbol.repository_id == repository_id)
    if name:
        stmt = stmt.where(Symbol.name.ilike(f"%{name}%"))
    if kind:
        stmt = stmt.where(Symbol.kind == kind)
    stmt = stmt.offset(skip).limit(limit).order_by(Symbol.name.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{repository_id}/dependencies", response_model=List[CodeDependencyRead])
async def list_repository_dependencies(
    repository_id: uuid.UUID,
    source_path: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
) -> List[CodeDependency]:
    stmt = select(CodeDependency).where(CodeDependency.repository_id == repository_id)
    if source_path:
        stmt = stmt.where(CodeDependency.source_path == source_path)
    stmt = stmt.offset(skip).limit(limit).order_by(CodeDependency.created_at.asc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{repository_id}/architecture", response_model=ArchitectureOverviewResponse)
async def get_repository_architecture(
    repository_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ArchitectureOverviewResponse:
    # 1. Fetch files and symbols
    files_stmt = select(SourceFile).where(SourceFile.repository_id == repository_id)
    files = list((await db.execute(files_stmt)).scalars().all())

    if not files:
        # Return empty architecture response
        return ArchitectureOverviewResponse(
            repository_id=repository_id,
            file_count=0,
            symbol_count=0,
            dependency_count=0,
            languages={},
            major_components=[],
            relationships=[],
        )

    # 2. Fetch all symbols and dependencies
    symbols_stmt = select(Symbol).where(Symbol.repository_id == repository_id)
    all_symbols = list((await db.execute(symbols_stmt)).scalars().all())

    deps_stmt = select(CodeDependency).where(CodeDependency.repository_id == repository_id)
    all_deps = list((await db.execute(deps_stmt)).scalars().all())

    # Group by file_id
    file_symbols: dict[uuid.UUID, list[Symbol]] = {f.id: [] for f in files}
    for s in all_symbols:
        if s.file_id in file_symbols:
            file_symbols[s.file_id].append(s)

    file_deps: dict[uuid.UUID, list[CodeDependency]] = {f.id: [] for f in files}
    for d in all_deps:
        if d.source_file_id in file_deps:
            file_deps[d.source_file_id].append(d)

    # Convert to ParsedFileResults for analyzer
    parsed_files = [
        ParsedFileResult(
            path=f.path,
            language=f.language,
            symbols=[
                ExtractedSymbol(
                    name=s.name,
                    kind=s.kind.value,
                    line_start=s.line_start,
                    line_end=s.line_end,
                    signature=s.signature,
                    docstring=s.docstring,
                )
                for s in file_symbols.get(f.id, [])
            ],
            dependencies=[
                ExtractedDependency(
                    target_path=d.target_path,
                    imported_symbol=d.imported_symbol,
                    kind=d.kind.value,
                )
                for d in file_deps.get(f.id, [])
            ],
        )
        for f in files
    ]

    analyzer = RelationshipAnalyzer()
    arch = analyzer.analyze_repository(parsed_files)

    return ArchitectureOverviewResponse(
        repository_id=repository_id,
        file_count=arch.file_count,
        symbol_count=arch.symbol_count,
        dependency_count=arch.dependency_count,
        languages=arch.languages,
        major_components=[
            ComponentOverview(
                name=c.name,
                path=c.path,
                symbol_count=c.symbol_count,
                file_count=c.file_count,
                dependencies=c.dependencies,
                tested_by=c.tested_by,
            )
            for c in arch.major_components
        ],
        relationships=[
            ComponentRelationshipSchema(
                source_name=r.source_name,
                source_path=r.source_path,
                target_name=r.target_name,
                target_path=r.target_path,
                type=r.type,
            )
            for r in arch.relationships
        ],
    )
