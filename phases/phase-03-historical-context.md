# Phase 3 — Historical + Engineering Context

## Goal

Extend the current-system context layer with evidence that explains how the software became what it is.

Core question:

> How did it get here?

## Prerequisites

Phase 2 complete.

## Product Model

```text
Current System
      +
Historical Context
      +
Engineering Context
      ↓
Project Intelligence
```

## Tasks

### Git Ingestion
- Ingest commit history
- Associate commits with changed files and symbols
- Extract commit messages and author metadata
- Support incremental history sync

### Pull Requests & Issues
- Ingest pull request titles, descriptions, and review discussions
- Ingest issue titles, descriptions, and comments
- Link PRs to issues and commits

### Engineering Artifacts
- Index markdown/documentation files
- Index ADRs and architecture records
- Extract design constraints and requirements

### Relationships & Evolution
- Connect current components/symbols to historical changes
- Build feature evolution timelines
- Link test changes to bug fixes

### Vector & Semantic Layer
- Generate embeddings for commits, PRs, issues, docs
- Store in pgvector
- Build hybrid retrieval (keyword + vector + graph traversal)

## Acceptance Criteria

- [ ] Git history can be ingested and linked to current components
- [ ] PRs, issues, and docs can be queried and retrieved
- [ ] Timeline of a component or symbol can be reconstructed
- [ ] Hybrid retrieval returns relevant historical evidence for a query
- [ ] All unit/integration tests pass
