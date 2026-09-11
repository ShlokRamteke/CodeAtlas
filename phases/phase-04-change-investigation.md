# Phase 4 — Change Investigation Engine

## Goal

Turn current-system, historical, and engineering context into the core
**Pre-Change Investigation** workflow: help developers understand what they are
about to change, why the relevant code exists, how it evolved, what depends on
it, and what consequences or hidden constraints should be considered before
implementation.

This is the key product differentiator.

## Prerequisites

Phase 3 complete.

## Core Investigation Pipeline

```text
Change Intent ("Replace Stripe integration with another payment provider")
    ↓
Target Identification
    ↓
Dependency / Caller Expansion (blast radius)
    ↓
Tests + API + Configuration Mapping
    ↓
Historical Changes & Origin Commits
    ↓
PRs / Issues / ADR Decisions
    ↓
Co-change / Hidden-coupling Signals
    ↓
Evidence Ranking
    ↓
Bounded LLM Synthesis (1–3 model calls)
    ↓
Verification & Citation Checks
    ↓
Pre-Change Investigation Brief
```

## Tasks

### 1. Investigation Engine
- [x] **PH4-01: Bounded Investigation Engine & Planner** *(Completed)*
  - Build bounded LangGraph workflow with strict 1–3 model call limits.
  - Parse change intent (natural language query, diff, or file list) into normalized targets.
- [x] **PH4-02: Blast Radius & Co-Change Hidden Coupling** *(Completed)*
  - Compute static upstream and downstream call graph reachability.
  - Mine Git commit diff co-changes to identify hidden coupling partners (frequency $> 60\%$, $\tau = 180\text{d}$ half-life decay).
  - Flag unexplained coupling warnings when proposed changes omit historical partner files.

- [x] **PH4-03: Quantitative Change Risk & Defect Pressure** *(Completed)*
  - Compute Kamei empirical metrics ($LA, LD, NF, ND, NS$).
  - Calculate Shannon churn entropy ($H(P)$) to score dispersion vs focus.
  - Mine historical defect pressure (20,000-commit deep walk with exponential recency decay $\tau = 365\text{d}$).
- [x] **PH4-04: Guarding Test & Verification Gap Analyzer** *(Completed)*
  - Map static call paths and dependencies from tests to modified symbols and files.
  - Compute reach-ranked test ordering (tests exercising the highest number of changed files prioritized).
  - Detect *Untested Changes* and *Stale Test Candidates*.

- [ ] **PH4-05: Intent Archaeology & Invariant Synthesis**
  - Link ADRs, RFC 2119 design invariants, PR rationale, and origin commits.
  - Distinguish governing vs superseded decisions to explain *why* constraints exist.
- [ ] **PH4-06: Token Budgeting & Dual-Format Projection**
  - Implement token-budgeted distillation with priority shedding and recoverable omission markers (`[ref#<id>]`).
  - Project canonical `ProjectContext` into Human-facing Markdown and dense Agent-facing JSON.
- [ ] **PH4-07: Concurrent Branch Overlap & Merge Conflict Detector**
  - Query open pull requests and active branches touching target files or their direct blast radius.
  - Flag concurrent in-flight changes to prevent merge conflicts before code is written.
- [ ] **PH4-08: Independent Change Decomposition**
  - Evaluate weakly-connected components across the dependency subgraph of proposed modified files.
  - Suggest splitting large, unrelated change bundles into independent, modular pull requests.
- [ ] **PH4-09: Code Ownership & Reviewer Recommender**
  - Calculate authorship concentration over modified and blast-radius files using historical `CommitFileChange` blame.
  - Recommend domain experts and reviewers best qualified to inspect the proposed change.
- [ ] **PH4-10: C4 Architecture & Dependency Export**
  - Generate clean C4 container/component models and Mermaid diagram definitions from canonical `ProjectContext`.
  - Provide automated, portable architectural export for engineering documentation.


### 2. Specialized Workflows
- [ ] **Pre-Change Investigation Brief** — Core product workflow: investigate a proposed change and generate a comprehensive brief.
- [ ] **Why Does This Exist?** — Focused investigation: explain why a workaround, pattern, or dependency was introduced.
- [ ] **Feature Archaeology** — Focused investigation: trace how a capability evolved over time.

### 3. Evidence, Claims & Verification
- [ ] Classify claims: fact, inference, unknown.
- [ ] Attach Evidence IDs to every non-trivial claim.
- [ ] Verify citations against underlying source entities.
- [ ] Score investigation confidence and identify explicit gaps/unknowns.

### 4. Pre-Change Investigation Brief Output Structure
The engine produces a structured brief containing:
- Change scope (targets, normalized symbols)
- Quantitative change risk (Kamei score, Shannon entropy, defect pressure)
- Affected components (direct & transitive blast radius)
- Dependency and call paths (inbound callers & outbound callees)
- Reach-ranked guarding tests & verification gap alerts
- Historical context & origin commits
- Related PRs / issues / predecessor discussions
- Hidden coupling / co-change partner warnings
- Known constraints (ADRs, RFC 2119 invariants, governing status)
- Important unknowns & ambiguous boundaries
- Recommended pre-implementation checklist
- Evidence citations and line-level source locations

## Acceptance Criteria & Definition of Done

- [ ] A developer can provide a proposed change and receive a grounded investigation brief covering affected scope, relationships, historical context, constraints, important signals, unknowns, and source evidence.
- [ ] Quantitative change risk score (Kamei metrics + Shannon entropy + defect pressure) is computed deterministically without LLM calls.
- [ ] Historical co-change detection alerts on omitted partner files.
- [ ] Guarding tests are reach-ranked and verification gaps flagged.
- [ ] Every non-trivial claim is linked to verified evidence with citations.
- [ ] Token-budgeted JSON output allows coding agents to operate within strict token limits with recoverable omission tokens.
- [ ] Token usage, model, and latency are tracked per investigation.
- [ ] All unit/integration tests pass.
