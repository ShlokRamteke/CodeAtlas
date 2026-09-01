# Phase 3 — Historical + Engineering Context

## Goal

Extend the canonical current-system context layer with historical and engineering evidence that explains how the software became what it is.

Core question:

> **How did this software/component get here?**

Phase 3 finds and organizes the deterministic evidence. Phase 4 uses AI to explain it.

---

## Target Architecture

```text
Current Project Context
        ↓
Git History (Commits, Authors, Timestamps)
        ↓
Commit → PR → Issue Relationships
        ↓
Historical Retrieval & Engineering Context (Docs, ADRs)
        ↓
Enriched ProjectContext
        ↓
Historical Timeline / Developer View
```

---

## Tasks Breakdown

### PH3-01 — Git History Indexing (Completed)
Build the historical dataset:
- [x] Ingest commits, changed files, diff stats, author identities, timestamps.
- [x] Build file-level history and identify introducing commit for each file/entity.
- [x] `GitHistoryIndexer` service with deterministic file/component evolution timeline.
- [x] REST endpoints (`/commits`, `/files/{path}/history`, `/components/{path}/history`).
- [x] Interactive Git History tab & File Evolution Inspector in Next.js UI.
- [x] Output: Current entities can be linked to Git history.


### PH3-02 — Commit → PR → Issue Linking (Completed)
Connect historical artifacts:
```text
Code / Entity
     ↓
   Commit
     ↓
  Pull Request
     ↓
   Issue
```
- [x] `ReferenceExtractor` parsing PR and issue reference patterns from commits and PR bodies (`Fixes #123`, `Merge pull request #45`, `PR #45`, `GH-101`, `resolves #99`).
- [x] Models & Alembic migration `0004_add_pr_issue_links` (`CommitPullRequestLink`, `CommitIssueLink`, `PullRequestIssueLink`).
- [x] `HistoricalLinker` service resolving bidirectional Code → Commit → PR → Issue lineage and unlinked cross-references.
- [x] `GitHubRepoFetcher` fetching PRs and Issues via GitHub REST API.
- [x] REST endpoints (`GET /pull-requests`, `GET /issues`, `GET /trace/{file_path:path}`, `POST /pull-requests/ingest`, `POST /issues/ingest`).
- [x] Frontend interactive Traceability, PRs, and Issues views with cross-referenced chips in Next.js UI.
- [x] Output: A developer can trace a change beyond the commit itself.

### PH3-03 — Historical Retrieval
Add deterministic retrieval specifically for historical questions:
- Search commits by message, author, file path, date range.
- Search PRs and issues by keyword and status.
- Find historical change events scoped to a specific component or symbol.
- Retrieve relevant historical evidence records without invoking an LLM.
- Output: A component or query retrieves relevant historical evidence.

### PH3-04 — Engineering Context
Add non-Git engineering context:
- Index `README.md`, `docs/`, architecture docs.
- Index ADRs (Architecture Decision Records) if present.
- Extract design constraints and testing rationale.
- Output: Unified knowledge consisting of Current System + History + Engineering Context.

### PH3-05 — Enrich ProjectContext
Key integration task. Extend the single canonical `ProjectContext` with historical and contextual evidence:
```text
ProjectContext
├── Current State (Files, Symbols, Languages)
├── Relationships (Imports, Callers, Dependencies)
├── Tests (Test suites, Test bindings)
├── Historical Changes (Commits, Authors, Timelines)
├── Related PRs (Pull requests, Discussions)
├── Related Issues (Issues, Labels, Resolving commits)
├── Documentation (Docs, ADRs, Constraints)
└── Evidence (Grounded provenance records)
```
- Do not create `HistoricalContext` as a separate competing model.

### PH3-06 — Historical Timeline / Developer View
Expose the result interactively to the developer:
- Interactive timeline showing component milestones (e.g. Introduction &rarr; Feature additions &rarr; Refactors).
- Every event links directly to evidence (commits, PRs, issues, ADRs).
- Full interactive UI view on Next.js frontend.

---

## Phase 3 Definition of Done

A task is complete only when:

```text
Select component
      ↓
Current Project Context
      ↓
Historical events discovered
      ↓
Relevant commits/PRs/issues linked
      ↓
Engineering context added
      ↓
Timeline/evidence displayed
```

And the user can answer:

> **"How did this component get here?"**

without an LLM.
