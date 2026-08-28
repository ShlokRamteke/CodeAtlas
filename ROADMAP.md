# Roadmap

## Overall Goal

Build a SaaS that helps developers **understand unfamiliar software before they change it**.

The product combines:

```text
Current System
      +
Historical Context
      +
Engineering Context
      ↓
Evidence-backed Understanding
```

History is a major differentiator and marketing hook, but the product is broader than Git-history analysis.

## End-to-End MVP

```text
GitHub
→ deterministic analysis
→ current + historical + engineering context
→ retrieval
→ context building
→ agentic investigation
→ answer + cited evidence
→ web UI / MCP
```

## Guiding Principles

1. Build only what is needed for the current phase.
2. Index deterministically where possible; use AI for synthesis and reasoning.
3. Keep the agent workflow bounded.
4. Keep the context minimal.
5. Ground every non-trivial claim in evidence.
6. Support both human understanding and agent reasoning.

---

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

---

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
- current-system Context Builder

### Done when
A repository can be indexed and its current structure can be queried and summarized for humans and LLMs.

---

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
- retrieval layer

### Done when
A developer or agent can trace how a component, symbol, or behavior evolved over time.

---

## Phase 4 — Archaeology & Investigation

### Goal
Build the AI investigation engine.

This phase answers:

> **Why is the software like this, and what should I know before changing it?**

### Includes
- bounded LangGraph workflow
- read-only investigation tools
- Context Builder
- evidence extraction
- claim classification
- confidence scoring
- Pre-Change Briefs
- "Why does this exist?"

### Done when
The system can reliably investigate an unfamiliar component or question and return a grounded answer with evidence citations.

---

## Phase 5 — SaaS Core

### Goal
Make the product a usable, secure multi-tenant application.

### Includes
- GitHub App onboarding
- auth / orgs / teams
- repository permissions
- async indexing pipeline
- caching
- rate limiting / token tracking
- audit logging
- settings

### Done when
A user can log in, install the GitHub App, select repositories, and use the product securely.

---

## Phase 6 — MCP Integration

### Goal
Allow external AI coding assistants to query Project Archaeologist.

### Includes
- MCP server
- read-only tools
- authentication / tenant checks
- structured investigation summaries

### Done when
Cursor/Claude Desktop/Windsurf can invoke Project Archaeologist to understand a component or design reason.

---

## Phase 7 — Evaluation & Production Hardening

### Goal
Validate quality, speed, safety, and reliability.

### Includes
- evaluation benchmark
- groundedness testing
- historical accuracy
- latency/cost tracking
- security audit
- performance tuning

### Done when
The product meets quality, security, and cost targets.

---

## Current Status

See [`STATUS.md`](file:///Users/shlok/Projects/Archelogiest/STATUS.md).
