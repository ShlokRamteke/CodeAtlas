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
- [ ] Build bounded LangGraph workflow
- [ ] Change-intent input & target identification
- [ ] Bounded investigation planner
- [ ] Dependency & impact tracing
- [ ] Historical correlation & co-change signals
- [ ] Multi-source evidence ranking
- [ ] Enforce max 1–3 model calls per normal investigation

### 2. Workflows
- [ ] **Pre-Change Investigation Brief** — Core product workflow: investigate a proposed change and generate a comprehensive brief
- [ ] **Why Does This Exist?** — Focused investigation: explain why a workaround, pattern, or dependency was introduced
- [ ] **Feature Archaeology** — Focused investigation: trace how a capability evolved over time

### 3. Evidence, Claims & Verification
- [ ] Classify claims: fact, inference, unknown
- [ ] Attach Evidence IDs to every non-trivial claim
- [ ] Verify citations against underlying source entities
- [ ] Score investigation confidence and identify explicit gaps/unknowns

### 4. Pre-Change Investigation Brief Output Structure
The engine produces a structured brief containing:
- Change scope
- Affected components
- Dependency and call paths
- Relevant tests
- Historical context
- Related PRs / issues / decisions
- Historical failures or reversions where discoverable
- Hidden coupling or co-change signals
- Known constraints (ADRs, RFC 2119 invariants)
- Important unknowns
- Recommended areas to inspect before implementation
- Evidence citations and source locations

## Acceptance Criteria & Definition of Done

- [ ] A developer can provide a proposed change and receive a grounded investigation brief covering affected scope, relationships, historical context, constraints, important signals, unknowns, and source evidence.
- [ ] "Why does this exist?" investigation returns grounded explanation with cited evidence.
- [ ] Every non-trivial claim is linked to verified evidence.
- [ ] Token usage, model, and latency are tracked per investigation.
- [ ] All unit/integration tests pass.
