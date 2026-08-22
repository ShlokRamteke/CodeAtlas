# Project Archaeologist — Roadmap

## Overall Goal

Build a SaaS that helps developers **understand unfamiliar software before they
change it**.

The product combines:

```text
Current System
      +
Historical Context
      +
Engineering Context
      ↓
AI Archaeological Investigation
      ↓
Evidence-backed Understanding
```

The history layer is a major differentiator and marketing hook, but the product
is broader than Git-history analysis.

## End-to-End MVP

```text
GitHub
→ deterministic analysis
→ current + historical + engineering context
→ hybrid retrieval
→ agentic investigation
→ evidence-backed explanation
→ SaaS UI
→ MCP
→ evaluation
```

## Development Principles

- Development is phase-based, not deadline-based.
- Day estimates are guidance only.
- Incomplete work carries forward.
- Do not advance a dependent phase until its definition of done is satisfied.
- Build vertical slices.
- Prove one useful workflow before broadening the product.
- Keep infrastructure minimal.
- Keep model calls bounded.
- Do not build future-phase functionality early.

## Phase 1 — Foundation

### Goal
Create the application, database, contracts, and development workflow.

### Outcome
A stable foundation for all later product work.

### Done when
- frontend runs
- backend runs
- database migrations work
- shared contracts exist
- CI works

## Phase 2 — Repository Understanding

### Goal
Build the current-system model of a repository.

This phase answers:

> **What is this software and how does it work today?**

### Includes
- GitHub connection
- repository ingestion
- AST/code analysis
- symbols
- dependencies
- tests
- APIs
- architecture relationships

### Done when
A repository can be indexed and its current structure can be queried.

## Phase 3 — Historical + Engineering Context

### Goal
Build the context that explains how the current system became what it is.

This phase answers:

> **How did it get here?**

### Includes
- Git history
- commits
- PRs
- issues
- documentation
- decision/context relationships
- embeddings
- hybrid retrieval

### Done when
The system can retrieve relevant current and historical evidence for
representative developer questions.

## Phase 4 — Archaeological Investigation

### Goal
Connect current-system understanding with historical/contextual evidence to
explain **why**.

This is the key differentiating AI layer.

### Includes
- Why Does This Exist?
- Investigation planner
- read-only investigation tools
- evidence correlation
- reasoning
- evidence verification
- confidence/uncertainty

### Done when
A developer can ask why a component or behavior exists and receive a grounded
explanation with evidence.

## Phase 5 — SaaS Experience

### Goal
Turn Project Intelligence into an easy-to-use developer product.

### Includes
- repository overview
- architecture explorer
- historical timeline
- investigation UI
- feature archaeology
- pre-change brief
- evidence navigation

### Done when
A developer can understand an unfamiliar repository through the SaaS without
manually traversing multiple GitHub surfaces.

## Phase 6 — MCP

### Goal
Make Project Archaeologist useful to coding agents.

### Includes
- MCP server
- read-only archaeology tools
- compact responses
- authorization

### Done when
A coding agent can ask for architecture/history/context before modifying code.

## Phase 7 — Evaluation + Hardening

### Goal
Make the system measurable, reliable, secure, and portfolio-ready.

### Includes
- golden repository
- evaluation dataset
- retrieval metrics
- history/why accuracy
- groundedness/citations
- cost/token tracking
- observability
- security review

### Done when
The end-to-end product is stable and its AI behavior is measurable.

## Phase Documents

- `phases/phase-01-foundation.md`
- `phases/phase-02-repository-understanding.md`
- `phases/phase-03-historical-context.md`
- `phases/phase-04-archaeology.md`
- `phases/phase-05-saas.md`
- `phases/phase-06-mcp.md`
- `phases/phase-07-evaluation.md`
