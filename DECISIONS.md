# Architecture Decisions

This file records significant technical and architectural decisions.

Keep entries short and factual. Do not record routine implementation choices.

---

## ADR-001 — PostgreSQL + pgvector

**Status:** Accepted

**Decision**

Use PostgreSQL as the primary database and pgvector for semantic retrieval in
the MVP.

**Reason**

The system needs relational data, metadata, evidence, and vector search.
Keeping these together minimizes infrastructure and operational complexity.

**Alternatives**

- Qdrant
- Pinecone
- Weaviate
- Neo4j

**Trade-off**

A dedicated vector/graph system may be introduced later if real workload
requires it.

---

## ADR-002 — Deterministic Analysis Before AI Reasoning

**Status:** Accepted

**Decision**

Use static/code/Git analysis for facts that can be extracted deterministically.
Use LLMs for interpretation, correlation, reasoning, and synthesis.

**Reason**

This improves accuracy and reduces token usage, latency, and nondeterminism.

**Trade-off**

The ingestion/indexing layer is more engineering-heavy.

---

## ADR-003 — Read-Only GitHub Access for MVP

**Status:** Accepted

**Decision**

Use a read-only GitHub App during the MVP.

**Reason**

The product investigates repositories and does not initially need write access.

**Trade-off**

Code modification and automatic PR creation are deferred.

---

## ADR-004 — Bounded Agentic Investigation

**Status:** Accepted

**Decision**

Use a controlled LangGraph workflow with explicit tools rather than a large
autonomous multi-agent swarm.

**Reason**

Project Archaeologist needs reliable, explainable investigations with low
token usage.

**Target**

Typically:
- optional planner call,
- one reasoning call,
- optional lightweight verification.

---

## ADR-005 — GitHub as Source of Truth

**Status:** Accepted

**Decision**

Treat the connected GitHub repository as authoritative. Store derived project
intelligence in the application.

**Reason**

Reduces unnecessary duplication of sensitive source data and keeps repository
state authoritative.

---

## ADR-006 — Living Project Documentation

**Status:** Accepted

**Decision**

Allow the coding agent to update `ARCHITECTURE.md`, `ROADMAP.md`, `STATUS.md`,
and `DECISIONS.md` when implementation genuinely changes them.

`PROJECT.md` may only be changed for explicit or clearly authorized product
scope changes.

**Reason**

Static documentation drifts as implementation evolves.

**Trade-off**

Automatic updates must be limited to substantive changes to avoid documentation
noise.

---

## ADR-007 — History Is a Core Intelligence Layer, Not the Entire Product

**Status:** Accepted

**Date:** 2026-08-22

**Decision**

Position Project Archaeologist as AI software understanding. Historical analysis is
a major differentiator and marketing hook, but the system also understands the
current architecture and surrounding engineering context.

**Reason**

Pure Git-history analysis is narrower and increasingly crowded. The product is
more valuable when it answers the broader developer question:

> What do I need to know about this software before I change it?

**Implication**

The architecture and roadmap should treat:
- current system understanding,
- historical context,
- engineering context

as first-class inputs to the same investigation engine.

---

## ADR-008 — Current-System Context Before AI Reasoning

**Status:** Accepted

**Decision**

Build a deterministic/language-aware Current System Context layer before introducing historical AI investigation.

**Reason**

Humans and LLMs do not need the entire codebase. They need a compact, trustworthy representation of the relevant part of the current system.

This reduces token usage, improves grounding, and avoids turning the project into a full compiler or autonomous code-understanding system.

**Implication**

Phase 2 focuses on:
- structural parsing,
- semantic resolution where useful,
- relationships,
- tests,
- current-system Context Builder.

Historical reasoning is added on top in later phases.

---

## ADR-009 — Unified Project Context

**Status:** Accepted

**Date:** 2026-08-25

**Decision**

Use a single canonical `ProjectContext` model as the authoritative shared context layer for both the human UI and AI/Agent prompt pipelines.

Do not maintain separate Human Context and LLM Context knowledge extraction pipelines.

```text
Project Knowledge
      ↓
Context Builder
      ↓
Project Context
   ├── Human UI (Markdown / Visual graph)
   └── AI / Agent (Token-efficient prompt serialization)
```

**Reason**

Maintaining divergent data structures or extraction logic for human exploration versus AI prompts introduces drift, inconsistent grounding, and duplicated indexing pipelines.

A single canonical `ProjectContext` model guarantees that:
1. Both human users and AI agents reason over the identical set of entities, relationship edges, evidence, confidence scores, and identified unknowns/gaps.
2. Serialization methods (`to_human_markdown()` and `to_llm_prompt()`) are deterministic projections of the same underlying data structure.
3. Unknowns (e.g. untested code, unresolved external dependencies, ambiguous types) are explicitly preserved and visible to both humans and LLMs.

---

## ADR-010 — Full-Stack Containerization Architecture

**Status:** Accepted

**Date:** 2026-08-28

**Decision**

Containerize the entire stack (FastAPI backend, Next.js 14 frontend, PostgreSQL with pgvector, and Adminer DB UI) into an orchestrated Podman / Docker Compose deployment (`compose.yaml` / `podman-compose.yml`) with automated migration execution and persistent storage volumes.

**Reason**

Managing disparate manual runtime processes (`uvicorn` local daemons, `next dev` background processes, standalone db containers) introduces port collision risks, environment drift across host OS configurations, and manual onboarding friction.

**Implication**

- The entire stack starts with a single command (`make up` or `podman compose up -d`).
- The backend entrypoint automatically checks database readiness and executes `alembic upgrade head` before serving traffic.
- Named volume `postgres_data` guarantees complete data persistence across container stop/start lifecycles.
- Host bind mounts preserve live hot-reloading for code development in `backend/` and `frontend/`.

---

## ADR-011 — Manifest-Aware Dependency Resolution

**Status:** Accepted

**Date:** 2026-08-28

**Decision**

Inspect project manifest files (`package.json`, `pyproject.toml`, `requirements.txt`) and standard library registries to differentiate declared 3rd-party dependencies from actual codebase gaps.

**Reason**

Treating all non-relative imports as "unresolved external package" gaps created false-positive noise in the Identified Unknowns panel (e.g., standard libraries or declared packages like `recharts`, `react`, `fastapi` being flagged as errors).

**Implication**

- Declared dependencies in `package.json` / `pyproject.toml` and runtime stdlibs are marked as resolved external boundaries without raising an uncertainty.
- Path aliases (`@/`, `~/`, `$lib/`, `src/`) resolve to local source files.
- The `undeclared_dependency` uncertainty is reserved specifically for undeclared ghost imports and broken relative paths.

---

## ADR-012 — Deterministic Cross-Artifact Traceability Engine

**Status:** Accepted

**Date:** 2026-08-28

**Decision**

Use deterministic regex pattern extraction and relational association models (`CommitPullRequestLink`, `CommitIssueLink`, `PullRequestIssueLink`) to establish bidirectional `Code -> Commit -> Pull Request -> Issue` traceability without requiring LLM calls during indexing.

**Reason**

Tracing code evolution beyond individual commit SHAs into Pull Requests, discussions, and originating Issues is a core requirement of historical archaeology. Relying on an LLM for reference extraction would be slow, non-deterministic, and costly. Regular expressions on standard GitHub merge formats and closing keywords (`Fixes #123`, `Merge pull request #45`, `(#45)`, `GH-101`) provide fast, 100% deterministic link discovery.

**Implication**

- Commits, PRs, and Issues can be ingested asynchronously in any order; unlinked references automatically reconcile when the corresponding artifact is indexed.
- The `HistoricalLinker` provides single-pass provenance tracing (`GET /trace/{file_path}`) across the full artifact lifecycle.

---

## ADR-013 — Primary GitHub GraphQL API for Repository & Historical Extraction

**Status:** Accepted

**Date:** 2026-08-28

**Decision**

Adopt GitHub GraphQL API v4 (`https://api.github.com/graphql`) as the primary data retrieval protocol for repository metadata, commit histories, parent graphs, pull requests, closing issue references, and issue trackers across all archaeology tasks, with seamless fallback to the REST API v3 when unauthenticated or for raw file content.

**Reason**

The GitHub REST API requires multiple roundtrips per repository (e.g. separate calls for repo metadata, commit list, individual commit file diffs, pull requests, and issues), quickly exhausting rate limits and introducing latency. The GraphQL API v4 enables batching the repository overview, branch references, commit parent graphs, associated pull requests, closing issue references, and labels into a **single HTTP network request**.

**Implication**

- When `GITHUB_TOKEN` is present, `GitHubRepoFetcher` queries the GraphQL endpoint, drastically reducing ingestion time and API rate consumption.
- If GraphQL returns 401 or no token is configured, the fetcher transparently falls back to public REST endpoints.
- All future repository analysis tasks (code structure, blame, history, PRs, issues, discussions) should prioritize GraphQL queries over multi-endpoint REST polling.

---

## ADR-014 — Deterministic Multi-Artifact Historical Retrieval & Evidence Ranking

**Status:** Accepted

**Date:** 2026-09-01

**Decision**

Implement a pure deterministic retrieval and ranking engine (`HistoricalRetriever`) for commits, pull requests, issues, and symbol evolutions without invoking an LLM.

**Reason**

Answering historical questions such as "When was symbol X added?", "Which PRs touched path Y?", or "Find commits related to Z" requires fast, deterministic, repeatable searches. Using LLMs for retrieval introduces latency, cost, and hallucination risks. PostgreSQL indexed relational queries, pattern matching, time range scoping, and score weighting provide instant, 100% grounded historical evidence records with exact citation links.

**Implication**

- Endpoints `/history/search`, `/history/retrieve`, and `/symbols/{name}/history` operate deterministically in sub-second latency.
- Evidence records conform to structured `HistoricalEvidenceRecord` interfaces with confidence scores, query matching scores, and provenance citations.
- Downstream AI reasoning in Phase 4 can consume these pre-filtered, structured evidence records directly in prompt context without performing brute-force repository searches.

---

## ADR-015 — Deterministic Engineering Context Indexing & Architectural Invariants

**Status:** Accepted

**Date:** 2026-09-08

**Decision**

Deterministically index engineering documentation, Architecture Decision Records (ADRs), and extract design constraints/invariants (RFC 2119 directives categorized into Security, Architecture, Performance, Testing, and Data Integrity) without LLM calls during indexing.

**Reason**

Non-Git engineering context (`README.md`, `ARCHITECTURE.md`, `docs/`, `DECISIONS.md`, ADRs) holds the design intent and constraints behind why code exists. Parsing document structure, ADR statuses, and RFC 2119 imperative statements (`MUST`, `MUST NOT`, `SHALL`, `NEVER`, `INVARIANT`) deterministically ensures high performance, zero API costs during ingestion, and absolute groundedness without hallucinations.

**Implication**

- `EngineeringContextParser` and `EngineeringContextIndexer` extract structured `EngineeringDocument` and `DesignConstraint` models into Postgres.
- Design constraints are linked directly to source documents with line-level citations.
- REST endpoints and frontend visualizers allow both human inspection and downstream LLM agents in Phase 4 to reference verified architectural constraints.



