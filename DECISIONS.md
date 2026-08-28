# Architecture Decisions

This file records significant technical and architectural decisions.

Keep entries short and factual. Do not record routine implementation choices.

---

## ADR-001 — PostgreSQL + pgvector

**Status:** Accepted

**Decision**

Use PostgreSQL as the primary database and pgvector for semantic retrieval in
the MVP.

**Reason**

The system needs relational data, metadata, evidence, and vector search.
Keeping these together minimizes infrastructure and operational complexity.

**Alternatives**

- Qdrant
- Pinecone
- Weaviate
- Neo4j

**Trade-off**

A dedicated vector/graph system may be introduced later if real workload
requires it.

---

## ADR-002 — Deterministic Analysis Before AI Reasoning

**Status:** Accepted

**Decision**

Use static/code/Git analysis for facts that can be extracted deterministically.
Use LLMs for interpretation, correlation, reasoning, and synthesis.

**Reason**

This improves accuracy and reduces token usage, latency, and nondeterminism.

**Trade-off**

The ingestion/indexing layer is more engineering-heavy.

---

## ADR-003 — Read-Only GitHub Access for MVP

**Status:** Accepted

**Decision**

Use a read-only GitHub App during the MVP.

**Reason**

The product investigates repositories and does not initially need write access.

**Trade-off**

Code modification and automatic PR creation are deferred.

---

## ADR-004 — Bounded Agentic Investigation

**Status:** Accepted

**Decision**

Use a controlled LangGraph workflow with explicit tools rather than a large
autonomous multi-agent swarm.

**Reason**

Project Archaeologist needs reliable, explainable investigations with low
token usage.

**Target**

Typically:
- optional planner call,
- one reasoning call,
- optional lightweight verification.

---

## ADR-005 — GitHub as Source of Truth

**Status:** Accepted

**Decision**

Treat the connected GitHub repository as authoritative. Store derived project
intelligence in the application.

**Reason**

Reduces unnecessary duplication of sensitive source data and keeps repository
state authoritative.

---

## ADR-006 — Living Project Documentation

**Status:** Accepted

**Decision**

Allow the coding agent to update `ARCHITECTURE.md`, `ROADMAP.md`, `STATUS.md`,
and `DECISIONS.md` when implementation genuinely changes them.

`PROJECT.md` may only be changed for explicit or clearly authorized product
scope changes.

**Reason**

Static documentation drifts as implementation evolves.

**Trade-off**

Automatic updates must be limited to substantive changes to avoid documentation
noise.

---

## ADR-007 — History Is a Core Intelligence Layer, Not the Entire Product

**Status:** Accepted

**Date:** 2026-08-22

**Decision**

Position Project Archaeologist as AI software understanding. Historical analysis is
a major differentiator and marketing hook, but the system also understands the
current architecture and surrounding engineering context.

**Reason**

Pure Git-history analysis is narrower and increasingly crowded. The product is
more valuable when it answers the broader developer question:

> What do I need to know about this software before I change it?

**Implication**

The architecture and roadmap should treat:
- current system understanding,
- historical context,
- engineering context

as first-class inputs to the same investigation engine.

---

## ADR-008 — Current-System Context Before AI Reasoning

**Status:** Accepted

**Decision**

Build a deterministic/language-aware Current System Context layer before introducing historical AI investigation.

**Reason**

Humans and LLMs do not need the entire codebase. They need a compact, trustworthy representation of the relevant part of the current system.

This reduces token usage, improves grounding, and avoids turning the project into a full compiler or autonomous code-understanding system.

**Implication**

Phase 2 focuses on:
- structural parsing,
- semantic resolution where useful,
- relationships,
- tests,
- current-system Context Builder.

Historical reasoning is added on top in later phases.

---

## ADR-009 — Unified Project Context

**Status:** Accepted

**Date:** 2026-08-25

**Decision**

Use a single canonical `ProjectContext` model as the authoritative shared context layer for both the human UI and AI/Agent prompt pipelines.

Do not maintain separate Human Context and LLM Context knowledge extraction pipelines.

```text
Project Knowledge
      ↓
Context Builder
      ↓
Project Context
   ├── Human UI (Markdown / Visual graph)
   └── AI / Agent (Token-efficient prompt serialization)
```

**Reason**

Maintaining divergent data structures or extraction logic for human exploration versus AI prompts introduces drift, inconsistent grounding, and duplicated indexing pipelines.

A single canonical `ProjectContext` model guarantees that:
1. Both human users and AI agents reason over the identical set of entities, relationship edges, evidence, confidence scores, and identified unknowns/gaps.
2. Serialization methods (`to_human_markdown()` and `to_llm_prompt()`) are deterministic projections of the same underlying data structure.
3. Unknowns (e.g. untested code, unresolved external dependencies, ambiguous types) are explicitly preserved and visible to both humans and LLMs.

