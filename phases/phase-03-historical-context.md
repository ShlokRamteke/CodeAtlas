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

### PH3-01 — Git History Indexing
Build the historical dataset:
- Ingest commits, changed files, diff stats, author identities, timestamps.
- Build file-level history and identify introducing commit for each file/entity.
- Output: Current entities can be linked to Git history.

### PH3-02 — Commit → PR → Issue Linking
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
- Parse PR and issue reference patterns from commit messages (e.g. `Fixes #123`, `Merge pull request #45`).
- Ingest GitHub PR metadata (title, body, author, merged_at) and issue metadata (title, body, labels, state).
- Output: A developer can trace a change beyond the commit itself.

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
