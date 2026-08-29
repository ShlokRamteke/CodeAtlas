from __future__ import annotations

import os
import uuid
from typing import List, Optional


from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.context_builder.builder import CurrentSystemContextBuilder
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
    ComponentBriefSchema,
    ComponentOverview,
    ComponentRelationshipSchema,
    ConnectGitHubRequest,
    ConnectGitHubResponse,
    ContextBriefResponse,
    IngestFilesRequest,
    ProjectContextRead,
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

        # 3b. Ingest Git History, PRs, and Issues (GraphQL / REST)
        try:
            from app.history.git_indexer import GitHistoryIndexer
            from app.history.historical_linker import HistoricalLinker

            linker = HistoricalLinker()
            indexer = GitHistoryIndexer()

            # Attempt single-pass batched GraphQL query first
            bundle = await fetcher.fetch_repo_bundle_graphql(
                owner=owner,
                repo=name,
                github_token=payload.github_token,
            )

            if bundle:
                commits, prs, issues = bundle
                if prs:
                    await linker.index_pull_requests(repo.id, prs, db)
                if issues:
                    await linker.index_issues(repo.id, issues, db)
                if commits:
                    await indexer.index_commits(repo.id, commits, db)
            else:
                # Fallback to individual endpoints
                prs = await fetcher.fetch_public_repo_pull_requests(
                    owner=owner,
                    repo=name,
                    github_token=payload.github_token,
                )
                if prs:
                    await linker.index_pull_requests(repo.id, prs, db)

                issues = await fetcher.fetch_public_repo_issues(
                    owner=owner,
                    repo=name,
                    github_token=payload.github_token,
                )
                if issues:
                    await linker.index_issues(repo.id, issues, db)

                commits = await fetcher.fetch_public_repo_commits(
                    owner=owner,
                    repo=name,
                    github_token=payload.github_token,
                )
                if commits:
                    await indexer.index_commits(repo.id, commits, db)
        except Exception:
            pass

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


@router.post("/{repository_id}/reindex", response_model=ConnectGitHubResponse)
async def reindex_repository(
    repository_id: uuid.UUID,
    github_token: Optional[str] = Query(None, description="Optional GitHub Personal Access Token"),
    db: AsyncSession = Depends(get_db),
) -> ConnectGitHubResponse:
    """
    Re-indexes an existing repository:
    Fetches fresh files, AST symbols, commit history, pull requests, and issues via GitHub GraphQL/REST.
    """
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repository_id} not found.",
        )

    fetcher = GitHubRepoFetcher()
    owner = repo.owner
    name = repo.name
    token = github_token or os.getenv("GITHUB_TOKEN")

    try:
        # 1. Fetch & ingest source files
        files, default_branch = await fetcher.fetch_public_repo_files(
            owner=owner,
            repo=name,
            github_token=token,
        )


        engine = IngestionEngine(db)
        arch = await engine.ingest_files(repo.id, files)

        # 2. Ingest Commits, PRs, and Issues (GraphQL / REST)
        try:
            from app.history.git_indexer import GitHistoryIndexer
            from app.history.historical_linker import HistoricalLinker

            linker = HistoricalLinker()
            indexer = GitHistoryIndexer()

            bundle = await fetcher.fetch_repo_bundle_graphql(
                owner=owner,
                repo=name,
                github_token=token,
            )

            if bundle:
                commits, prs, issues = bundle
                if prs:
                    await linker.index_pull_requests(repo.id, prs, db)
                if issues:
                    await linker.index_issues(repo.id, issues, db)
                if commits:
                    await indexer.index_commits(repo.id, commits, db)
            else:
                prs = await fetcher.fetch_public_repo_pull_requests(
                    owner=owner,
                    repo=name,
                    github_token=token,
                )
                if prs:
                    await linker.index_pull_requests(repo.id, prs, db)

                issues = await fetcher.fetch_public_repo_issues(
                    owner=owner,
                    repo=name,
                    github_token=token,
                )
                if issues:
                    await linker.index_issues(repo.id, issues, db)

                commits = await fetcher.fetch_public_repo_commits(
                    owner=owner,
                    repo=name,
                    github_token=token,
                )
                if commits:
                    await indexer.index_commits(repo.id, commits, db)
        except Exception:
            pass

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
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Reindex failed: {str(exc)}",
        ) from exc




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
                confidence=r.confidence,
                resolution_method=r.resolution_method,
            )
            for r in arch.relationships
        ],
    )


@router.get("/{repository_id}/context-brief", response_model=ContextBriefResponse)
async def get_repository_context_brief(
    repository_id: uuid.UUID,
    component: Optional[str] = Query(None, description="Optional component or file path filter"),
    db: AsyncSession = Depends(get_db),
) -> ContextBriefResponse:
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    files_stmt = select(SourceFile).where(SourceFile.repository_id == repository_id)
    files = list((await db.execute(files_stmt)).scalars().all())

    symbols_stmt = select(Symbol).where(Symbol.repository_id == repository_id)
    symbols = list((await db.execute(symbols_stmt)).scalars().all())

    deps_stmt = select(CodeDependency).where(CodeDependency.repository_id == repository_id)
    deps = list((await db.execute(deps_stmt)).scalars().all())

    # Build relationship graph
    file_symbols: dict[uuid.UUID, list[Symbol]] = {f.id: [] for f in files}
    for s in symbols:
        if s.file_id in file_symbols:
            file_symbols[s.file_id].append(s)

    file_deps: dict[uuid.UUID, list[CodeDependency]] = {f.id: [] for f in files}
    for d in deps:
        if d.source_file_id in file_deps:
            file_deps[d.source_file_id].append(d)

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

    builder = CurrentSystemContextBuilder()
    files_dict = [{"id": f.id, "path": f.path, "language": f.language} for f in files]
    symbols_dict = [
        {"id": s.id, "file_id": s.file_id, "name": s.name, "kind": s.kind.value, "line_start": s.line_start, "line_end": s.line_end, "signature": s.signature}
        for s in symbols
    ]
    deps_dict = [
        {"source_file_id": d.source_file_id, "target_path": d.target_path, "imported_symbol": d.imported_symbol, "kind": d.kind.value}
        for d in deps
    ]
    rels_dict = [
        {"source_name": r.source_name, "source_path": r.source_path, "target_name": r.target_name, "target_path": r.target_path, "type": r.type}
        for r in arch.relationships
    ]

    # Construct Canonical ProjectContext
    target_type = "component" if component else "repository"
    target_name = component if component else repo.full_name
    proj_ctx = builder.build_project_context(
        target_id=str(repo.id),
        target_name=target_name,
        target_type=target_type,
        files=files_dict,
        symbols=symbols_dict,
        dependencies=deps_dict,
        relationships=rels_dict,
        component_filter=component,
    )

    project_context_read = ProjectContextRead.model_validate(proj_ctx.to_dict())

    # Build component list
    components_list = [
        ComponentBriefSchema(

            name=c.name,
            path=c.path,
            language="typescript",
            symbol_count=c.symbol_count,
            symbols=[],
            dependencies=[{"target": d, "kind": "internal", "confidence": "1.0"} for d in c.dependencies],
            callers=[],
            tests=[c.tested_by] if c.tested_by else [],
            human_summary=f"Component `{c.name}` with {c.symbol_count} symbols.",
            llm_context=f"COMPONENT: {c.name} | SYMBOLS: {c.symbol_count}",
        )
        for c in arch.major_components
    ]

    return ContextBriefResponse(
        repository_id=repo.id,
        full_name=repo.full_name,
        file_count=len(files),
        symbol_count=len(symbols),
        dependency_count=len(deps),
        languages=arch.languages,
        components=components_list,
        human_summary=proj_ctx.to_human_markdown(),
        llm_context=proj_ctx.to_llm_prompt(),
        project_context=project_context_read,
    )


@router.get("/{repository_id}/context", response_model=ProjectContextRead)
async def get_repository_context(
    repository_id: uuid.UUID,
    component: Optional[str] = Query(None, description="Optional component or file path filter"),
    db: AsyncSession = Depends(get_db),
) -> ProjectContextRead:
    """
    Returns the canonical Unified ProjectContext for a repository or component.
    Single source of truth consumed by Human UI and AI/Agent prompt pipelines.
    """
    repo = await db.get(Repository, repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository not found",
        )

    files_stmt = select(SourceFile).where(SourceFile.repository_id == repository_id)
    files = list((await db.execute(files_stmt)).scalars().all())

    symbols_stmt = select(Symbol).where(Symbol.repository_id == repository_id)
    symbols = list((await db.execute(symbols_stmt)).scalars().all())

    deps_stmt = select(CodeDependency).where(CodeDependency.repository_id == repository_id)
    deps = list((await db.execute(deps_stmt)).scalars().all())

    # Build relationship graph
    file_symbols: dict[uuid.UUID, list[Symbol]] = {f.id: [] for f in files}
    for s in symbols:
        if s.file_id in file_symbols:
            file_symbols[s.file_id].append(s)

    file_deps: dict[uuid.UUID, list[CodeDependency]] = {f.id: [] for f in files}
    for d in deps:
        if d.source_file_id in file_deps:
            file_deps[d.source_file_id].append(d)

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

    builder = CurrentSystemContextBuilder()
    files_dict = [{"id": f.id, "path": f.path, "language": f.language} for f in files]
    symbols_dict = [
        {"id": s.id, "file_id": s.file_id, "name": s.name, "kind": s.kind.value, "path": next((f.path for f in files if f.id == s.file_id), ""), "line_start": s.line_start, "line_end": s.line_end, "signature": s.signature}
        for s in symbols
    ]
    deps_dict = [
        {"source_file_id": d.source_file_id, "source_path": d.source_path, "target_path": d.target_path, "imported_symbol": d.imported_symbol, "kind": d.kind.value, "confidence": 1.0}
        for d in deps
    ]
    rels_dict = [
        {"source_name": r.source_name, "source_path": r.source_path, "target_name": r.target_name, "target_path": r.target_path, "type": r.type, "confidence": r.confidence, "resolution_method": r.resolution_method}
        for r in arch.relationships
    ]

    target_type = "component" if component else "repository"
    target_name = component if component else repo.full_name
    proj_ctx = builder.build_project_context(
        target_id=str(repo.id),
        target_name=target_name,
        target_type=target_type,
        files=files_dict,
        symbols=symbols_dict,
        dependencies=deps_dict,
        relationships=rels_dict,
        component_filter=component,
    )

    return ProjectContextRead.model_validate(proj_ctx.to_dict())


