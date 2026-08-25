# Phase 4 — Archaeology & Investigation

## Goal

Use current-system context from Phase 2 plus historical/engineering context from Phase 3 to explain **why** the software is the way it is.

This is the key AI/product differentiation layer.

## Prerequisites

Phase 3 complete.

## Core Investigation

```text
User Question
    ↓
Planner
    ↓
Read-only Tools (code + history + docs)
    ↓
Evidence Pool
    ↓
Context Builder
    ↓
Bounded LLM Reasoning
    ↓
Evidence Verification
    ↓
Answer + Citations
```

## Tasks

### Investigation Engine
- Build bounded LangGraph workflow
- Implement investigation planner
- Connect read-only investigation tools
- Enforce max 1–3 model calls per investigation

### Archaeology Workflows
- **Why Does This Exist?** — Explain why a workaround, pattern, or dependency was introduced
- **Pre-Change Brief** — Summarize everything a developer should know before modifying a component
- **Feature Archaeology** — Trace how a feature was built, modified, and maintained over time
- **Architecture Overview** — Synthesize current structure + historical intent

### Evidence & Claims
- Classify claims (fact, inference, unknown)
- Attach Evidence IDs to every non-trivial claim
- Verify citations against source data
- Score investigation confidence

### User Experience
- Investigation UI with collapsible evidence panel
- Timeline visualization
- Source code / commit / PR deep links
- Export / share investigation brief

## Acceptance Criteria

- [ ] "Why does this exist?" investigation returns grounded explanation with cited evidence
- [ ] Pre-Change Brief identifies relevant history, tests, dependencies, and caveats
- [ ] Every non-trivial claim is linked to verified evidence
- [ ] Token usage and latency are tracked per investigation
- [ ] All unit/integration tests pass
