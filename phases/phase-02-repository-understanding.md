# Phase 2 — Repository Understanding

## Goal

Build a **reliable current-system context layer**.

The phase should answer:

> What is this software and how does it work today?

The goal is not perfect whole-repository semantic understanding. The goal is a trustworthy model that helps humans, retrieval, and later AI reasoning.

## Product Output

```text
Repository
    ↓
Deterministic + language-aware analysis
    ↓
Current System Model
    ↓
Context Builder
    ├── Human View
    └── LLM Context
```

## Prerequisites

Phase 1 complete.

## Architecture

See `ARCHITECTURE.md` section 4: "Current System Context Layer".

## Tasks

### Ingestion Baseline
- [x] Read repository files deterministically
- [x] Extract repository structure
- [x] Incremental indexing via content hashes
- [x] Secret scanning before persistence

### Structural Code Analysis
- [x] Tree-sitter parser for structural extraction
- [x] Language support: TypeScript/JavaScript first, Python
- [x] Extract functions, classes, interfaces, methods, types
- [x] Extract file-level imports and exports
- [x] Map basic call and reference relationships

### Semantic Resolution (Language-Aware)
- [x] Resolve internal module imports
- [x] Map dependencies across files
- [x] Track relationship confidence where applicable

### Test & Architecture Mapping
- [x] Locate and associate unit/integration tests
- [x] Identify entry points and APIs
- [x] Detect key components/services
- [x] Map component dependencies

### Current-System Context Builder
- [x] Produce compact component summaries
- [x] Support caller/dependency extraction
- [x] Output human-readable summary
- [x] Output LLM-optimized context block

### Storage & Query
- [x] Store normalized current-system models
- [x] Symbol query endpoints
- [x] Dependency/caller query endpoints
- [x] Component summary endpoints

## Acceptance Criteria

- [x] Repository can be ingested without executing user code
- [x] TypeScript/JavaScript codebase can be parsed into symbols and dependencies
- [x] Test files are associated with their target code where evident
- [x] Components and dependencies can be queried by API
- [x] Context Builder produces a compact briefing for a given component
- [x] Frontend can display the current-system architecture
- [x] All unit/integration tests pass
