# Phase 5 — Semantic Indexing & Decision Models

## Goal

Enrich the deterministic repository index with fast, typed, non-autoregressive "System One" decision models (Laya / ModernBERT / `/v1/systemone` protocol) running locally on CPU at sub-40ms latency and zero per-token cloud costs.

The phase answers:

> What are the architectural roles, semantic invariants, commit intents, and container boundaries across the codebase, without running expensive, slow, non-deterministic generative LLMs?

## Core Principles

1. **AST & History as Factual Anchor**: Tree-sitter AST relationships, file paths, and raw git diffs remain the deterministic truth. Decision models enrich metadata; they never invent edges.
2. **Strict Calibrated Thresholds**: Every decision requires a calibrated probability score ($P \in [0, 1]$). Only classifications with $P \ge 0.85$ are accepted.
3. **Graceful Fallback**: If the decision engine is unavailable, offline, or confidence is $< 0.85$, the system automatically falls back to deterministic rule heuristics without failing ingestion.
4. **Non-Autoregressive Speed**: Zero token-by-token text generation. Typed schemas (`choice`, `score`, `noul`) evaluated in parallel single-pass forward runs.

## Prerequisites

Phase 4 complete (Change Investigation Engine).

## Architecture & Protocol

See `ARCHITECTURE.md` section on "Semantic Indexing & System One Decision Pipeline".

The decision layer implements the open `/v1/systemone` specification:
```text
Raw Codebase & Docs
      ↓
Tree-sitter AST & Git Indexer (Deterministic Baseline)
      ↓
SystemOneClient (Laya / ModernBERT-large on local CPU / 40ms)
      ├── PH5-02: Symbol Architectural Role (controller, service, repository, entity)
      ├── PH5-03: Semantic Invariant Mining (security, data_integrity, performance)
      ├── PH5-04: Commit Intent & Bug-Fix Defect Mining (refines Kamei defect pressure)
      └── PH5-05: C4 Container Boundary Classification (monorepo container roles)
      ↓
Enriched ProjectContext & C4 Architecture Models
      ├── High-Fidelity Pre-Change Investigation (Phase 4 engine)
      └── Developer SaaS UI (Phase 6 web experience)
```

## Tasks

### PH5-01: System One Client & Protocol Adapter
- [x] Implement `SystemOneClient` supporting the `/v1/systemone` specification (`POST /v1/systemone` with `state` and typed `questions`).
- [x] Support question types: `choice` (categorical), `noul` (boolean yes/no), `score` (ordered numeric).
- [x] Calibrated probability parser extracting confidence metrics.
- [x] Deterministic fallback mechanism when confidence $< 0.85$ or connection fails.
- [x] Mock decision provider for fast unit/integration testing without running local model server in CI.

### PH5-02: Architectural Symbol Role Classifier (AST Indexing)
- [x] Define `ArchitecturalRole` enum (`controller`, `service`, `repository`, `entity`, `middleware`, `utility`).
- [x] Extend `tree_sitter_parser.py` and `relationship_analyzer.py` to batch-evaluate class/function symbols.
- [x] Extract symbol signature, decorators, method names, and docstring as decision state.
- [x] Persist `architectural_role` on `ContextEntity` model and database schemas.
- [x] Expose symbol role in symbol query endpoints and C4 component exports.

### PH5-03: Semantic Constraint & Invariant Mining (Documentation Indexing)
- [x] Extend `engineering_context_parser.py` to evaluate natural-language document sentences in markdown (`README.md`, `ARCHITECTURE.md`, `ADRs`).
- [x] Classify whether sentences constitute non-negotiable architectural invariants (`is_invariant: noul`).
- [x] Categorize invariant domain (`security`, `concurrency`, `data_integrity`, `performance`, `deployment`).
- [x] Determine RFC 2119 equivalent priority (`MUST`, `SHOULD`, `FORBIDDEN`).
- [x] Index natural rules that do not explicitly contain uppercase RFC keywords.

### PH5-04: Commit Intent & Historic Bug-Fix Defect Mining (Git History Indexing)
- [x] Extend `git_indexer.py` commit ingestion pipeline.
- [x] Classify commit intent: `bugfix`, `refactor`, `feature`, `chore`, `security_patch`.
- [x] Identify whether historical commits represent defect/regression repairs (`is_defect_fix: noul`).
- [x] Feed refined defect tags directly into Kamei defect pressure calculations (`app.history.change_risk`).

### PH5-05: C4 Container Boundary & Deployable Unit Classifier (Architecture Indexing)
- [x] Extend `c4_exporter.py` for monorepo and custom layout analysis (`packages/`, `services/`, `libs/`).
- [x] Evaluate directory listings and package manifests (`pyproject.toml`, `package.json`, `Dockerfile`).
- [x] Classify container types: `api`, `web_app`, `worker`, `database`, `shared_library`, `cli_tool`.
- [x] Eliminate manual directory mapping in C4 architecture exports.

### PH5-06: Containerized Local Serving & Performance Benchmark
- [x] Add `laya` service to `compose.yaml` (using `ghcr.io/nandakishorm/laya-serve` on port 8081).
- [x] Environment variable configuration (`DECISION_MODEL_URL`, `DECISION_MODEL_ENABLED`).
- [x] Benchmark test suite asserting sub-40ms execution on CPU.
- [x] End-to-end repository indexing regression tests verifying enriched metadata quality.

## Explicit Non-Goals

- Autoregressive generative chatting during indexing.
- Overriding Tree-sitter AST relationships with ungrounded predictions.
- Sending proprietary repository source to third-party cloud APIs during indexing (must remain 100% local).

## Acceptance Criteria & Definition of Done

- [x] `SystemOneClient` handles `choice`, `noul`, and `score` questions with calibrated probabilities.
- [x] Ingestion degrades gracefully to deterministic defaults when decision model is offline.
- [x] Code symbols receive verified `architectural_role` tags during indexing.
- [x] Unformatted natural-language constraints in docs are extracted into `DesignConstraint` records.
- [x] Commit history defect pressure reflects classified bugfix commits.
- [x] C4 container export correctly identifies non-standard container directories.
- [x] All unit, integration, and benchmark tests pass without regressions.
