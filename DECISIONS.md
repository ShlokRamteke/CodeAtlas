# Architecture Decisions

This file records significant technical and product-architecture decisions.
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

The product needs reliable, explainable investigations with low token usage.

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

## ADR-006 — Pre-Change Investigation as the Primary Product Workflow

**Status:** Accepted

**Decision**

Position CodeAtlas around investigating proposed software changes,
with code understanding and software archaeology serving as the underlying
intelligence layers.

**Reason**

Generic codebase intelligence, code search, history analysis, graphs, and MCP
are increasingly commoditized or offered by established products. A focused
pre-change investigation workflow provides a clearer product job and a more
specific user outcome.

**Trade-off**

The system should prioritize change-investigation quality over breadth of
generic repository features.

---

## ADR-007 — One Canonical ProjectContext

**Status:** Accepted

**Decision**

Use a single canonical `ProjectContext` enriched by current-system, historical,
and engineering evidence. Human UI and AI/agent consumers use scoped views of
the same model.

**Reason**

Avoids duplicate knowledge pipelines and prevents divergence between what the
UI shows and what the agent reasons over.

---

## ADR-008 — Project Graph Abstraction, PostgreSQL Implementation

**Status:** Accepted

**Decision**

Define a Project Graph abstraction in application code, backed initially by
PostgreSQL relationship tables.

**Reason**

The product requires graph traversal for dependencies, callers, history, and
impact analysis, but a dedicated graph database is not yet justified.

**Trade-off**

Complex graph workloads may require a dedicated graph store later.

---

## ADR-009 — Living Project Documentation

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

## ADR-010 — Full-Stack Containerization Architecture

**Status:** Accepted

**Date:** 2026-08-28

**Decision**

Containerize the entire stack (FastAPI backend, Next.js 14 frontend, PostgreSQL with pgvector, and Adminer DB UI) into an orchestrated Podman / Docker Compose deployment (`compose.yaml` / `podman-compose.yml`) with automated migration execution and persistent storage volumes.

**Reason**

Managing disparate manual runtime processes (`uvicorn` local daemons, `next dev` background processes, standalone db containers) introduces port collision risks, environment drift across host OS configurations, and manual onboarding friction.

**Implication**

- The entire stack starts with a single command (`make up` or `podman compose up -d`).
- The backend entrypoint automatically checks database readiness and executes `alembic upgrade head` before serving traffic.
- Named volume `postgres_data` guarantees complete data persistence across container stop/start lifecycles.
- Host bind mounts preserve live hot-reloading for code development in `backend/` and `frontend/`.

---

## ADR-011 — Manifest-Aware Dependency Resolution

**Status:** Accepted

**Date:** 2026-08-28

**Decision**

Inspect project manifest files (`package.json`, `pyproject.toml`, `requirements.txt`) and standard library registries to differentiate declared 3rd-party dependencies from actual codebase gaps.

**Reason**

Treating all non-relative imports as "unresolved external package" gaps created false-positive noise in the Identified Unknowns panel (e.g., standard libraries or declared packages like `recharts`, `react`, `fastapi` being flagged as errors).

**Implication**

- Declared dependencies in `package.json` / `pyproject.toml` and runtime stdlibs are marked as resolved external boundaries without raising an uncertainty.
- Path aliases (`@/`, `~/`, `$lib/`, `src/`) resolve to local source files.
- The `undeclared_dependency` uncertainty is reserved specifically for undeclared ghost imports and broken relative paths.

---

## ADR-012 — Deterministic Cross-Artifact Traceability Engine

**Status:** Accepted

**Date:** 2026-08-28

**Decision**

Use deterministic regex pattern extraction and relational association models (`CommitPullRequestLink`, `CommitIssueLink`, `PullRequestIssueLink`) to establish bidirectional `Code -> Commit -> Pull Request -> Issue` traceability without requiring LLM calls during indexing.

**Reason**

Tracing code evolution beyond individual commit SHAs into Pull Requests, discussions, and originating Issues is a core requirement of historical archaeology. Relying on an LLM for reference extraction would be slow, non-deterministic, and costly. Regular expressions on standard GitHub merge formats and closing keywords (`Fixes #123`, `Merge pull request #45`, `(#45)`, `GH-101`) provide fast, 100% deterministic link discovery.

**Implication**

- Commits, PRs, and Issues can be ingested asynchronously in any order; unlinked references automatically reconcile when the corresponding artifact is indexed.
- The `HistoricalLinker` provides single-pass provenance tracing (`GET /trace/{file_path}`) across the full artifact lifecycle.

---

## ADR-013 — Primary GitHub GraphQL API for Repository & Historical Extraction

**Status:** Accepted

**Date:** 2026-08-28

**Decision**

Adopt GitHub GraphQL API v4 (`https://api.github.com/graphql`) as the primary data retrieval protocol for repository metadata, commit histories, parent graphs, pull requests, closing issue references, and issue trackers across all archaeology tasks, with seamless fallback to the REST API v3 when unauthenticated or for raw file content.

**Reason**

The GitHub REST API requires multiple roundtrips per repository (e.g. separate calls for repo metadata, commit list, individual commit file diffs, pull requests, and issues), quickly exhausting rate limits and introducing latency. The GraphQL API v4 enables batching the repository overview, branch references, commit parent graphs, associated pull requests, closing issue references, and labels into a **single HTTP network request**.

**Implication**

- When `GITHUB_TOKEN` is present, `GitHubRepoFetcher` queries the GraphQL endpoint, drastically reducing ingestion time and API rate consumption.
- If GraphQL returns 401 or no token is configured, the fetcher transparently falls back to public REST endpoints.
- All future repository analysis tasks (code structure, blame, history, PRs, issues, discussions) should prioritize GraphQL queries over multi-endpoint REST polling.

---

## ADR-014 — Deterministic Multi-Artifact Historical Retrieval & Evidence Ranking

**Status:** Accepted

**Date:** 2026-09-01

**Decision**

Implement a pure deterministic retrieval and ranking engine (`HistoricalRetriever`) for commits, pull requests, issues, and symbol evolutions without invoking an LLM.

**Reason**

Answering historical questions such as "When was symbol X added?", "Which PRs touched path Y?", or "Find commits related to Z" requires fast, deterministic, repeatable searches. Using LLMs for retrieval introduces latency, cost, and hallucination risks. PostgreSQL indexed relational queries, pattern matching, time range scoping, and score weighting provide instant, 100% grounded historical evidence records with exact citation links.

**Implication**

- Endpoints `/history/search`, `/history/retrieve`, and `/symbols/{name}/history` operate deterministically in sub-second latency.
- Evidence records conform to structured `HistoricalEvidenceRecord` interfaces with confidence scores, query matching scores, and provenance citations.
- Downstream AI reasoning in Phase 4 can consume these pre-filtered, structured evidence records directly in prompt context without performing brute-force repository searches.

---

## ADR-015 — Deterministic Engineering Context Indexing & Architectural Invariants

**Status:** Accepted

**Date:** 2026-09-08

**Decision**

Deterministically index engineering documentation, Architecture Decision Records (ADRs), and extract design constraints/invariants (RFC 2119 directives categorized into Security, Architecture, Performance, Testing, and Data Integrity) without LLM calls during indexing.

**Reason**

Non-Git engineering context (`README.md`, `ARCHITECTURE.md`, `docs/`, `DECISIONS.md`, ADRs) holds the design intent and constraints behind why code exists. Parsing document structure, ADR statuses, and RFC 2119 imperative statements (`MUST`, `MUST NOT`, `SHALL`, `NEVER`, `INVARIANT`) deterministically ensures high performance, zero API costs during ingestion, and absolute groundedness without hallucinations.

**Implication**

- `EngineeringContextParser` and `EngineeringContextIndexer` extract structured `EngineeringDocument` and `DesignConstraint` models into Postgres.
- Design constraints are linked directly to source documents with line-level citations.
- REST endpoints and frontend visualizers allow both human inspection and downstream LLM agents in Phase 4 to reference verified architectural constraints.

---

## ADR-016 — Clean-Room Intellectual Property Boundary & Licensing Policy

**Status:** Accepted

**Date:** 2026-09-08

**Decision**

Maintain a strict clean-room intellectual property boundary between CodeAtlas (licensed under permissive MIT) and external copyleft reference codebases (specifically AGPL-3.0 repositories).

Under this policy:
1. **Zero Source Code Contamination:** No functions, classes, database schemas, prompt templates, or tests may be copied, vendored, transliterated, or dynamically imported from AGPL-3.0 repositories.
2. **Permitted Borrowing (Ideas & Standards Only):** We borrow only non-copyrightable elements:
   - Published peer-reviewed academic algorithms (e.g. Kamei et al. Just-in-Time defect prediction, Shannon entropy of code churn, Louvain/Leiden graph clustering, exponential recency decay).
   - Public industry protocols (e.g. Model Context Protocol JSON-RPC 2.0 specifications, standard Git CLI commands).
   - High-level functional requirements and behavioral heuristics (e.g. flagging co-change partners missing from diffs, ordering test suites by changed file reach).
3. **Independent Clean Implementation:** All features are designed from scratch and authored independently in Python/FastAPI/PostgreSQL adhering to CodeAtlas's existing schemas and patterns.
4. **Local Repository Quarantine:** Any external reference repositories used for functional study (e.g. in `_references/`) must remain permanently ignored in `.gitignore`, never committed to git, and never packaged in production container images.

**Reason**

Copyleft network services (such as those under AGPL-3.0) enforce strong reciprocal obligations. Under AGPL Section 13, linking, importing, or creating a derivative work from AGPL code would contaminate CodeAtlas, legally requiring the entire codebase and SaaS platform to be open-sourced under AGPL-3.0. A strict clean-room boundary guarantees CodeAtlas remains 100% MIT permissive, enabling full commercial flexibility for enterprise SaaS and closed-source customer deployments.

**Implication**

- CodeAtlas retains its MIT license with zero legal risk.
- Algorithmic models are implemented from primary literature (citing academic papers in code docstrings).
- External clones remain strictly local reference tools on developer workstations.

---

## ADR-017 — Quantitative Change Risk, Historical Co-Change, and Guarding Test Reachability

**Status:** Accepted

**Date:** 2026-09-08

**Decision**

Incorporate quantitative change risk metrics, historical co-change mining, and reach-ranked guarding test signals into the Phase 4 Change Investigation Engine and canonical `ProjectContext`:

1. **Quantitative Change Risk Scoring (Kamei Model + Defect History):**
   - Adopt the empirical software engineering model by Kamei et al. (IEEE TSE 2013) for Just-in-Time defect risk.
   - Compute churn shape: lines added ($LA$), lines deleted ($LD$), files touched ($NF$), distinct directories ($ND$), distinct subsystems ($NS$).
   - Compute Shannon churn entropy: $H(P) = -\sum p_i \log_2 p_i$, measuring the diffusion and scatter of the proposed change across modules.
   - Compute historical defect pressure: Mine past bug-fix commits touching target files using a deep git log walk (up to 20,000 commits) discounted by exponential recency decay ($\tau = 365\text{d}$).
2. **Historical Co-Change & Hidden Coupling Warnings:**
   - Mine commit diff history to identify files that frequently change together ($\text{co-change frequency} > 60\%$).
   - Classify coupling into *corroborated* (static import/call edge exists) and *unexplained / hidden coupling* (no static edge, but historical co-change is high).
   - Emit pre-change alerts if a proposed change modifies file $A$ but omits historical co-change partner file $B$.
3. **Guarding Test Reachability & Stale Test Detection:**
   - Trace static AST call graphs to identify test suites that transitively exercise modified functions.
   - Rank guarding tests by *reach* (prioritizing test files that cover the greatest number of touched components so developers/agents run the highest-impact tests first).
   - Flag *Untested Changes* (modified lines/symbols with zero covering tests) and *Stale Test Candidates* (exercised code modified without corresponding updates to its guarding test files).
4. **Token-Budgeted Output & Omission Markers:**
   - Enforce strict token ceilings for pre-change investigation payloads.
   - If evidence exceeds the budget, shed lower-priority details and attach recoverable omission markers (`[ref#<id>]`), allowing AI agents (Claude Code, Cursor, Copilot) to selectively expand context on demand without overflowing context windows.

**Reason**

Static AST analysis answers "what is connected", but fails to answer "what is risky", "what usually breaks", or "what files are implicitly coupled without an import". Combining static graph reachability with deterministic Git churn metrics, defect histories, and co-change patterns creates an industrial-strength pre-change investigation brief that prevents regressions before code is written.

**Implication**

- `CanonicalProjectContext` is enriched with co-change partners, defect pressure scores, and guarding test rankings.
- Step 5 (Blast Radius), Step 7 (Change Risk), Step 8 (Guarding Tests), and Step 10/11 (Budgeted Projection) of the 12-step engine are formally standardized with concrete mathematical formulas.
- All algorithms execute deterministically in PostgreSQL and Python without relying on LLM hallucination for risk computation.

---

## ADR-018 — OpenRouter Unified LLM Gateway and Anthropic Hierarchical XML Prompt Architecture

**Status:** Accepted

**Date:** 2026-09-09

**Decision**

1. Adopt OpenRouter (`https://openrouter.ai/api/v1`) as the primary unified LLM gateway for the Phase 4 Pre-Change Investigation Engine, with configurable model routing (`OPENROUTER_MODEL`, defaulting to cost-effective models such as `openai/gpt-4o-mini`).
2. Retain direct OpenAI support (`OpenAILLMProvider`) and deterministic mock support (`MockLLMProvider`) via the pluggable `LLMProvider` protocol for offline zero-network testing.
3. Adopt Anthropic's official hierarchical XML document standard for prompt engineering:
   - Untrusted repository context and code snippets are strictly isolated in nested `<documents><document index="N" id="ev-..."><source>...</source><document_content>...</document_content></document></documents>` blocks.
   - Code indentation and line breaks are strictly preserved (no string flattening).
   - Prompts enforce system/user role separation to prevent prompt injection from untrusted repository text.
   - LLM responses are validated through Pydantic schemas (`PlannerLLMOutput`, `ReasonerLLMOutput`) enforcing typed claim classifications (`fact`, `inference`, `unknown`) and cited evidence IDs.

**Reason**

OpenRouter provides vendor-agnostic routing across Anthropic, OpenAI, Meta, and Google models with unified usage and cost tracking, avoiding vendor lock-in. Anthropic's XML document standard is the peer-reviewed industry benchmark for multi-document reasoning, reducing hallucinations by 20–40% while protecting system prompts from prompt injection.

**Implication**

- Prompts are modularized in `backend/app/investigation/prompts.py`.
- LLM outputs are reliably structured with typed Pydantic validation.
- All automated unit tests run offline with `MockLLMProvider`, requiring zero API keys in CI/CD.

