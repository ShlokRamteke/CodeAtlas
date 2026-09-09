# Project Archaeologist

> **Investigate software before you change it.**

Project Archaeologist is an AI-powered software change-investigation system.
It reconstructs the current codebase, its relationships, and its history so
developers can understand the consequences and constraints of a proposed
change before implementation.

## The Problem

When you inherit unfamiliar software, the important context is rarely in one
place. It is spread across source code, dependencies, tests, Git history, PRs,
issues, documentation, and architectural decisions.

Project Archaeologist connects these sources and turns them into a grounded
investigation.

## Core Workflow

```text
GitHub Repository
      ↓
Deterministic Code + History Analysis
      ↓
Project Knowledge
      ↓
Canonical ProjectContext + Project Graph (PostgreSQL)
      ↓
Change Investigation
      ↓
Evidence + Reasoning + Verification
      ↓
Pre-Change Investigation Brief
```

## Example

> “I want to replace Stripe in the payment service. What should I know before
> changing it?”

The system investigates affected code, callers, dependencies, tests, related
historical changes, PRs/issues, and other relevant evidence, then presents a
scoped brief with sources and unknowns.

## What It Understands

- current code structure and symbols
- imports, calls, dependencies, and relationships
- APIs and tests where detectable
- Git history and file evolution
- pull requests and issues
- documentation and engineering decisions
- historical and change-related evidence

## Current Functioning & Live Capabilities

The system currently has a fully operational foundation (Phase 1), repository understanding layer (Phase 2), and deep historical & engineering context layer (Phase 3 tasks PH3-01 to PH3-04) running locally across a multi-container stack:

### 1. Interactive Web Application (Next.js 14)
- **Repository Ingestion & Management:** Ingest local codebases or remote GitHub repositories using the GraphQL v4 & REST v3 protocols.
- **Component & Architecture Explorer:** Interactive breakdown of modules, directories, files, and Tree-sitter AST symbols with line spans and confidence ratings.
- **Project Graph & Dependency Visualizer:** Visualizes static call graphs, import graphs, and dependency relationships with manifest-aware gap demarcation (flags actual ghost imports while treating declared packages and stdlib as resolved).
- **Git History & Origin Commit Inspector:** File-by-file evolution view identifying the exact introducing commit (origin commit), author, line delta, and commit message.
- **Artifact Traceability Sub-Views:** Interactive cross-referencing between Commits, Pull Requests, and Issues (`Code -> Commit -> PR -> Issue`) with direct GitHub links and resolution keywords (`Fixes #123`, `Merged in PR #45`).
- **Deterministic Historical Search & Symbol Evolution:** Sub-second searching across commits, PRs, and issues by keyword, author, path, state, and dates, plus symbol evolution timelines with ranked evidence cards.
- **Engineering Context Viewer:** Architecture Decision Records (ADRs) catalog, RFC 2119 architectural invariants matrix (categorized into Security, Architecture, Performance, Testing, and Data Integrity), and documentation search.

### 2. Backend Engines & Services (FastAPI + PostgreSQL)
- **Tree-sitter Structural AST Parsing:** Deterministic extraction of functions, classes, interfaces, imports, and exports for TypeScript/JavaScript and Python.
- **Git History Indexing (`GitHistoryIndexer`):** Git log extraction and diff tracking with `CommitFileChange` relational mapping (`added`, `modified`, `deleted`, `renamed`).
- **Artifact Traceability (`HistoricalLinker` & `ReferenceExtractor`):** Single-pass deterministic regex link discovery reconciling commits, PRs, and issues without LLM hallucination.
- **Deterministic Historical Retrieval (`HistoricalRetriever`):** Multi-attribute search, symbol milestone extraction, and score-ranked `HistoricalEvidenceRecord` generation.
- **Engineering Context Engine (`EngineeringContextIndexer` & `EngineeringContextParser`):** Markdown parsing, ADR status/decider indexing, and RFC 2119 imperative directive extraction with line-level citations.

### 3. Quickstart & Local Execution

The entire stack is containerized with automatic database migrations and persistent storage volumes:

```bash
# Start all services (PostgreSQL + pgvector, FastAPI backend, Next.js frontend, Adminer DB UI)
make up
# Or using Podman / Docker directly:
podman compose -f podman-compose.yml up -d
# docker compose -f compose.yaml up -d
```

- **Frontend UI:** `http://localhost:3000`
- **FastAPI Documentation (Swagger):** `http://localhost:8000/docs`
- **Adminer DB Manager:** `http://localhost:8080`

### 4. Verified Automated Test Suite
- **52 passing automated pytest tests** covering AST parsing, graph traversal, Git history indexing, PR/Issue linking, historical retrieval, engineering context extraction, Kamei change risk scoring, co-change hidden coupling detection, and reach-ranked guarding tests.
- Clean TypeScript contracts typecheck (`packages/contracts`) and Next.js production build (`packages/web` / `frontend`).

## Development Context

- `AGENTS.md` — coding-agent development rules
- `PROJECT.md` — product intent and scope
- `ARCHITECTURE.md` — technical design
- `ROADMAP.md` — phase plan
- `STATUS.md` — current implementation state
- `DECISIONS.md` — significant decisions
- `phases/` — phase-specific goals and acceptance criteria

For coding-agent work, start with `AGENTS.md` and `STATUS.md`.

## Current Status

See [`STATUS.md`](file:///Users/shlok/Projects/Archelogiest/STATUS.md).

## License

[MIT License](file:///Users/shlok/Projects/Archelogiest/LICENSE) — Copyright (c) 2026 Shlok Prashant Ramteke.

