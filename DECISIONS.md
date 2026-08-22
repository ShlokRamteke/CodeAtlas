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

## ADR-006 — History Is a Core Intelligence Layer, Not the Entire Product

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

## ADR-007 — Podman Container Runtime

**Status:** Accepted

**Date:** 2026-08-22

**Decision**

Use Podman as the local container runtime and compose engine (`podman-compose.yml` / `compose.yaml`).

**Reason**

Rootless, daemonless container execution aligning with security best practices and developer environment standards.

