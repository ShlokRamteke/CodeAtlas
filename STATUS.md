# Development Status

## Current Phase

Phase 3 — Historical + Engineering Context

## Current Task

PH3-01 — Git History Indexing

## Status

IN PROGRESS


## Product Focus

The product goal is to help developers understand unfamiliar software.

History is a major differentiator and marketing hook, but not the entire
product. The core system combines current architecture, historical context,
engineering context, and AI reasoning.

## Completed

- **Phase 1 — Foundation**:
  - Git repository bootstrap and `.gitignore` setup
  - Podman Compose environment with `docker.io/pgvector/pgvector:pg16`
  - Shared TypeScript contracts and schema types (`packages/contracts`)
  - FastAPI backend with async database engine, models, schemas, and endpoints (`backend/`)
  - Alembic database migrations with PostgreSQL pgvector support
  - Next.js 14 frontend application with dark theme and API client (`frontend/`)
  - GitHub Actions CI workflow for backend and frontend (`.github/workflows/ci.yml`)

- **Phase 2 — Repository Understanding**:
  - Tree-sitter AST parser (`ASTCodeParser`) supporting TypeScript, TSX, JavaScript, and Python (`backend/app/parser/ast_parser.py`)
  - Deterministic symbol extraction (functions, classes, interfaces, types, methods, docstrings, line numbers)
  - Dependency and import extraction (internal, external, relative imports) with confidence and extraction provenance
  - Relationship and test linker (`RelationshipAnalyzer`) mapping tests to source modules and constructing component architecture graphs
  - Canonical Unified `ProjectContext` model (`project_context.py`) unifying Human UI and AI/Agent prompt pipelines into a single source of truth
  - Deterministic detection and tracking of architectural unknowns & uncertainties (untested modules, external uninspected packages, empty files)
  - `CurrentSystemContextBuilder` with dual projection rendering (`to_human_markdown()` and token-efficient `to_llm_prompt()`)
  - REST endpoints for repository ingestion (`/ingest`, `/connect-github`), canonical context (`/context`), symbol query (`/symbols`), dependencies (`/dependencies`), and architecture overview (`/architecture`)
  - Frontend interactive `ArchitectureExplorer` component with component cards, live symbol search, relationship graph, and dedicated Unified ProjectContext viewer with unknowns panel
  - Complete automated test suite with 100% pass rate (16/16 pytest tests, zero type errors in contracts and frontend)


## Remaining

- Begin Phase 3 — Historical Intelligence (Git commit ingestion, PR discussions, issue links, evolution timeline).

## Blockers

None

## Next Action

Start Phase 3: Implement Git commit history analyzer and PR/issue timeline ingestion.

## Session Rule

Update this file after meaningful development sessions.

If work is incomplete:
- keep the task in progress,
- list remaining work,
- record blockers,
- set the next actionable step.

Do not advance phases until the current phase definition of done is satisfied.

## Last Updated

2026-08-22
