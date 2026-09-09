# Phase 3 — Historical + Engineering Context

## Goal

Enrich the canonical `ProjectContext` with evidence explaining how the current
system evolved and what engineering context surrounds it.

Core question:

> **How did this software/component get here?**

Phase 3 finds and organizes the deterministic evidence. Phase 4 uses AI to reason over it for change investigations.

---

## Target Architecture

```text
Current Project Context
        ↓
Git History (Commits, Authors, Timestamps, Introducing Commits)
        ↓
Commit → PR → Issue Traceability & Relationships
        ↓
Historical Retrieval & Engineering Context (Docs, ADRs, Constraints)
        ↓
Enriched Canonical ProjectContext
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
- [x] `GitHubRepoFetcher` fetching PRs and Issues via GitHub REST & GraphQL APIs.
- [x] REST endpoints (`GET /pull-requests`, `GET /issues`, `GET /trace/{file_path:path}`, `POST /pull-requests/ingest`, `POST /issues/ingest`).
- [x] Frontend interactive Traceability, PRs, and Issues views with cross-referenced chips in Next.js UI.
- [x] Output: A developer can trace a change beyond the commit itself.

### PH3-03 — Historical Retrieval (Completed)
Add deterministic retrieval specifically for historical questions:
- [x] Search commits by message, author, file path, date range.
- [x] Search PRs and issues by keyword, state, and labels.
- [x] Find historical change events and evolution timeline scoped to a specific component or symbol.
- [x] Retrieve ranked historical evidence records with provenance without invoking an LLM.
- [x] Output: A component or query retrieves relevant historical evidence.

### PH3-04 — Engineering Context (Completed)
Add non-Git engineering context:
- [x] Deterministic `EngineeringContextParser` parsing `README.md`, `docs/`, architecture docs, and ADRs without LLM.
- [x] Models `EngineeringDocument` and `DesignConstraint` with Alembic migration `0005_add_engineering_context`.
- [x] Extracted design constraints and architectural invariants using RFC 2119 imperatives categorized into Security, Architecture, Performance, Testing, and Data Integrity.
- [x] `EngineeringContextIndexer` service supporting documentation ingestion, ADR indexing, constraint querying, and keyword search.
- [x] REST endpoints (`/engineering/overview`, `/docs`, `/adrs`, `/constraints`, `/search`, `/ingest`).
- [x] Frontend interactive **Engineering Context** tab & `EngineeringContextViewer` component.
- [x] Output: Unified knowledge consisting of Current System + History + Engineering Context.

### PH3-05 — Enrich ProjectContext (Completed)
Key integration task. Extend the single canonical `ProjectContext` with historical and contextual evidence:
```text
ProjectContext
├── Current State (Files, Symbols, Languages)
├── Relationships (Imports, Callers, Dependencies)
├── Tests (Test suites, Test bindings)
├── Historical Changes (Commits, Authors, Timelines, Introducing Changes)
├── Related PRs (Pull requests, Discussions)
├── Related Issues (Issues, Labels, Resolving commits)
├── Documentation (Docs, ADRs, Architectural Invariants)
└── Evidence (Grounded provenance records)
```
- [x] Attach historical and engineering evidence directly to current-system entities (`introducing_commit`, `change_count`, `active_authors`, `related_adrs`).
- [x] Integrate multi-source evidence (`git_commit`, `pull_request`, `architecture_decision`, `design_constraint`) into canonical `ProjectContext`.
- [x] Preserve single canonical `ProjectContext` model with dual human and token-budgeted LLM prompt projections without competing context models.
- [x] Enriched `GET /api/v1/repositories/{id}/context` endpoint returning unified AST + Git history + PRs + Issues + ADRs + Constraints.

### PH3-06 — Historical Timeline / Developer View
Expose the result interactively to the developer:
- Interactive timeline showing component milestones (e.g. Introduction &rarr; Feature additions &rarr; Refactors).
- Every event links directly to evidence (commits, PRs, issues, ADRs).
- Full interactive UI view on Next.js frontend.

---

## Definition of Done

A task is complete only when:

```text
Select component / path
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

And relevant code can be traced into its history and supporting engineering evidence
with provenance, without requiring an LLM to establish basic historical facts.
