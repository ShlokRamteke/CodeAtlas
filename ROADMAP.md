# CodeAtlas — Roadmap

## Product Goal

Build an AI-powered SaaS that investigates a **proposed software change** by
connecting current code, relationships, history, and engineering evidence.

The primary deliverable is a grounded **Pre-Change Investigation Brief**.

## End-to-End MVP

```text
GitHub
→ deterministic code/history/doc analysis
→ Project Knowledge
→ canonical ProjectContext + Project Graph (PostgreSQL)
→ scoped retrieval
→ bounded investigation (LangGraph)
→ evidence verification
→ Pre-Change Investigation Brief
→ SaaS UI / MCP
→ evaluation
```

## Guiding Principles

1. Development is phase-based, not deadline-based.
2. Build vertical slices; do not start a dependent phase before prerequisites are satisfied.
3. Index deterministically where possible; use AI for synthesis and reasoning.
4. Keep the agent workflow bounded (typically 1–3 model calls per investigation).
5. Ground every non-trivial claim in verified evidence.
6. Support both human understanding and agent reasoning through scoped views of one canonical `ProjectContext`.
7. Treat the proposed change as the investigation task boundary; do not build generic codebase chat.
8. Do not build future-phase functionality early.

---

## Phase 1 — Foundation (Completed)

### Goal
Create the application skeleton, database baseline, contracts, and development workflow.

### Done when
- [x] frontend runs
- [x] backend runs
- [x] database migrations work
- [x] shared contracts exist
- [x] CI works

---

## Phase 2 — Repository Understanding (Completed)

### Goal
Build the deterministic **Current System Context**: a reliable structured representation of what the repository is and how its code is connected today.

### Core Work Completed
- [x] GitHub connection and repository ingestion
- [x] Tree-sitter AST parsing (TypeScript/JavaScript, Python)
- [x] Symbol extraction and source locations
- [x] File-level imports and exports
- [x] Call and reference relationships
- [x] Manifest-aware dependency resolution
- [x] Test and API mapping
- [x] Context Builder producing canonical `ProjectContext`
- [x] Storage in PostgreSQL relationship models

---

## Phase 3 — Historical + Engineering Context (Completed)

### Goal
Enrich the canonical `ProjectContext` with evidence explaining how the current system evolved and what engineering context surrounds it.

Core question:

> **How did this software/component get here?**

### Structured Tasks
- **PH3-01 — Git History Indexing** *(Completed)*: Commits, file histories, diff stats, author identities, introducing commit origin detection, and interactive evolution viewer.
- **PH3-02 — Commit → PR → Issue Linking** *(Completed)*: Deterministic regex reference extraction (`Fixes #123`, `Merge pull request #45`), bidirectional linking models, `HistoricalLinker` provenance traces (`Code -> Commit -> PR -> Issue`), and UI chips.
- **PH3-03 — Historical Retrieval** *(Completed)*: Deterministic multi-attribute historical search (commits, PRs, issues, symbol timeline) and ranked `HistoricalEvidenceRecord` synthesis without LLMs.
- **PH3-04 — Engineering Context** *(Completed)*: Deterministic documentation parsing (ADRs, RFC 2119 architectural invariants, design constraints).
- **PH3-05 — Enrich ProjectContext** *(Completed)*: Extend the single canonical `ProjectContext` with historical changes, PRs, issues, ADRs, and design constraints, attaching historical evidence directly to current entities.
- **PH3-06 — Historical Timeline / Developer View** *(Completed)*: Interactive component evolution timeline linking each event directly to verified evidence across commits, PRs, issues, and ADRs.

### Done when
Relevant code can be traced into its history and supporting engineering evidence with provenance, without requiring an LLM to establish basic historical facts.

---

## Phase 4 — Change Investigation Engine

### Goal
Turn current-system, historical, and engineering context into the core **Pre-Change Investigation** workflow.

### Structured Tasks
- **PH4-01 — Bounded Investigation Engine & Planner** *(Completed)*: Change intent parsing, bounded LangGraph state graph (1–3 model calls), OpenRouter gateway, Anthropic-standard hierarchical XML prompting.
- **PH4-02 — Blast Radius & Co-Change Hidden Coupling** *(Completed)*: Static upstream/downstream call graph reachability, recency-decayed co-change mining, and unexplained hidden coupling detection.
- **PH4-03 — Quantitative Change Risk & Defect Pressure** *(Completed)*: Unified diff parsing, Kamei empirical metrics ($LA, LD, NF, ND, NS$), Shannon churn entropy $H(P)$, and 20,000-commit deep walk defect pressure mining ($\tau = 365\text{d}$).
- **PH4-04 — Guarding Test & Verification Gap Analyzer** *(Completed)*: Test call path reachability, reach-ranking test ordering, untested change alerts, and stale test detection.
- **PH4-05 — Intent Archaeology & Invariant Synthesis** *(Completed)*: ADR constraint linking, governing vs superseded status, and rationale extraction.
- **PH4-06 — Token Budgeting & Dual-Format Projection**: Priority shedding, recoverable omission markers (`[ref#<id>]`), human Markdown and dense agent JSON projections.
- **PH4-07 — Concurrent Branch Overlap & Merge Conflict Detector**: In-flight branch inspection and merge collision warnings.
- **PH4-08 — Independent Change Decomposition**: Weakly-connected component subgraph evaluation and change decomposition suggestions.
- **PH4-09 — Code Ownership & Reviewer Recommender**: Historical blame concentration and qualified reviewer recommendations.
- **PH4-10 — C4 Architecture & Dependency Export**: Portable C4 component models and Mermaid architectural diagram exports.


### Done when
A developer can provide a proposed change and receive a grounded, evidence-backed investigation brief covering scope, historical context, constraints, risks/signals, and important unknowns.

---

## Phase 5 — SaaS Experience & Core

### Goal
Turn the change-investigation engine into a clear developer-facing web experience and secure multi-tenant SaaS product.

### Core Work
- Repository overview and health indicators
- Architecture / component explorer
- Historical timeline and evolution view
- Change-investigation entry flow (target + proposed change)
- Pre-Change Investigation Brief interactive UI
- GitHub App integration and multi-tenant isolation
- Asynchronous indexing workers (Inngest)
- Rate limiting, token tracking, and cost controls

### Done when
A developer can select a target, describe a proposed change, run an investigation, and inspect the resulting evidence-backed brief through the web UI.

---

## Phase 6 — MCP Integration

### Goal
Expose pre-change investigation capabilities to external AI coding assistants via Model Context Protocol (MCP).

### Tools
- `investigate_change(target, proposed_change)`
- `get_change_context(target)`
- `get_dependencies(entity_id)`
- `trace_feature(feature_name)`
- `search_history(query)`
- `get_related_issues(symbol_or_path)`
- `why_does_this_exist(symbol_or_path)`

### Done when
External coding agents (Cursor, Claude Desktop, Windsurf) can invoke CodeAtlas to investigate a proposed change or understand code rationale.

---

## Phase 7 — Evaluation & Production Hardening

### Goal
Measure whether the system reliably improves pre-change understanding and harden the system for real production use.

### Core Work
- Golden benchmark repositories and versioned change-investigation test questions
- Affected-component recall evaluation (blast-radius detection)
- Dependency and impact recall evaluation
- Historical retrieval and evidence accuracy evaluation
- Citation accuracy and groundedness testing (>95% verified citations)
- Token usage and cost tracking (<$0.05 per standard investigation)
- Latency optimization (<5s standard investigation)
- Observability and security audit

### Done when
The benchmark is repeatable, investigation quality is measurable, model usage is tracked, security boundaries are tested, and the core workflow is stable.

---

## Phase Documents

- `phases/phase-01-foundation.md`
- `phases/phase-02-repository-understanding.md`
- `phases/phase-03-historical-context.md`
- `phases/phase-04-change-investigation.md`
- `phases/phase-05-saas.md`
- `phases/phase-06-mcp.md`
- `phases/phase-07-evaluation.md`

## Current Status

See [`STATUS.md`](file:///Users/shlok/Projects/Archelogiest/STATUS.md).
