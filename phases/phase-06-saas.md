# Phase 6 — SaaS Experience & Core

## Goal

Turn the change-investigation engine into a clear, secure developer-facing web experience and multi-tenant SaaS product. Unify and expose all intelligence layers built across Phases 1–5 (Tree-sitter AST, component relationships, git history provenance, engineering ADR constraints, bounded LangGraph investigation, Kamei change risk, reach-ranked guarding tests, dual-format token budgeted projections, and System One semantic decisions) into a cohesive developer workflow.

## Prerequisites

Phase 4 complete (Change Investigation Engine) & Phase 5 complete (Semantic Indexing & Decision Models).

## Architecture & Product Workflow

```text
Phase 1–5 Core Intelligence Engine
├── Phase 2: Tree-sitter AST (Symbols, Decorators, Roles, File Callers & Dependencies)
├── Phase 3: Historical Provenance (Commits, PRs, Issues, ADRs, RFC 2119 Constraints)
├── Phase 4: Investigation Engine (Blast Radius, Kamei Risk, Guarding Tests, Invariants, Decomposition, Ownership)
└── Phase 5: System One (ModernBERT Roles, Defect Fix Mining, C4 Container Boundaries)
      │
      ▼
Canonical ProjectContext & Project Graph (PostgreSQL)
      │
      ├─────────────────────────────────────────────────────────────┐
      ▼                                                             ▼
Part A: SaaS Experience & Pre-Change Investigation UI          Part B: SaaS Core, Multi-Tenancy & Security
├── PH6-01: Repository Overview & Health Scorecard [Done]      ├── PH6-08: GitHub App (OAuth, Webhooks, Read-Only Sync)
├── PH6-02: Architecture & Component Explorer [Done]           ├── PH6-09: Multi-Tenant Data Isolation & Authorization
├── PH6-03: Historical Timeline & Evolution View [Done]        ├── PH6-10: Asynchronous Indexing Workers (Inngest)
├── PH6-04: Change-Investigation Entry Flow                    ├── PH6-11: Rate Limiting, Token Tracking & Cost Controls
├── PH6-05: Pre-Change Brief Interactive UI                    └── PH6-12: Caching Layer & Security Audit Logging
├── PH6-06: Evidence Navigation & Source Deep Links
└── PH6-07: Unknowns, Risk & Confidence Presentation
```

---

## Tasks

### Part A: SaaS Experience & Pre-Change Investigation UI

#### PH6-01: Repository Overview & Health Indicators *(Completed)*
- [x] Deterministic 6-dimension health scorecard (testing protection index, knowledge distribution / bus factor, defect pressure, architectural modularity, governance invariants, concurrent PR collision risk).
- [x] Composite 0–100 normalized health score with status tiers (`HEALTHY`, `STABLE`, `ATTENTION_NEEDED`).
- [x] Hotspot file detection aggregating historical commit churn and defect repair tags with risk classification (`high`, `medium`, `low`).
- [x] Top contributors and authorship blame distribution with maintainer roles.
- [x] Interactive executive dashboard in `RepositoryOverviewViewer.tsx` as default active view with 1-click investigation navigation.
- [x] REST endpoint `GET /api/v1/repositories/{id}/overview` returning `RepositoryOverviewResponse`.

#### PH6-02: Architecture & Component Explorer *(Completed)*
- [x] Component coupling metrics: inbound fan-in callers, outbound fan-out dependencies, and coupling density via `RelationshipAnalyzer`.
- [x] Architectural role classification: surfaces System One dominant roles (`service`, `controller`, `repository`, `entity`, `middleware`, `utility`).
- [x] Test protection status (`guarded` vs `untested`) and test bindings per component.
- [x] Dual-view UI in `ComponentExplorerViewer.tsx`: Component Directory Grid and Coupling Topology Matrix.
- [x] Interactive component inspection modal with AST symbols, signatures, line spans, contained files, and 1-click change investigation prefill.
- [x] REST endpoints `GET /api/v1/repositories/{id}/architecture` and `GET /api/v1/repositories/{id}/components/{component_path:path}/overview`.

#### PH6-03: Historical Timeline & Evolution View *(Completed)*
- [x] Repository-wide and component-scoped evolution timeline (`component_path="all"` vs specific path) in `GitHistoryIndexer`.
- [x] Multi-dimensional timeline telemetry (`TimelineStats`): total milestones, commits, ADRs, net churn (`+insertions / -deletions`), defect repair frequency, author counts, and timespan.
- [x] Monthly activity cadence ribbon (`TimelineVelocityItem`) with visual stacked histogram and 1-click month drilldown.
- [x] Milestone categories (`introduction`, `feature_addition`, `refactor`, `bug_fix`, `architectural_decision`, `maintenance`) with live count chips.
- [x] Touched files inspector on milestones with 1-click **Investigate Touched Files** prefill.
- [x] Interactive UI in `HistoricalTimelineViewer.tsx` promoted to dedicated top-level "Evolution Timeline" tab.
- [x] REST endpoint `GET /api/v1/repositories/{id}/timeline` returning `RepositoryTimelineResponse`.

#### PH6-04: Change-Investigation Entry Flow & Multi-Target Selector
- [ ] Interactive target selector using Phase 2 Tree-sitter AST files and symbols (replaces raw manual string typing).
- [ ] Component-scoped selection: pick an entire component to auto-populate target files.
- [ ] In-flight PR selection: 1-click target prefill from open pull requests and concurrent branches (Phase 4 concurrent overlap detection).
- [ ] Change intent templates: prefill common investigation queries ("Refactor API", "Migrate Database Schema", "Fix Defect", "Add Endpoint").
- [ ] Pre-flight validation & blast radius preview before launching full LangGraph model pipeline.

#### PH6-05: Pre-Change Investigation Brief Interactive UI
- [ ] Refined SaaS visual brief layout integrating all Phase 4 & 5 synthesized intelligence cards:
  - Scope & Intent Summary card (target files, symbols, normalized query).
  - Concrete Code Changes Blueprint (action tags, descriptions, code snippets, affected callers).
  - Kamei Quantitative Risk & Shannon Churn Entropy scorecard ($LA, LD, NF, ND, NS, H(P)$, defect pressure).
  - Guarding Tests & Reach-Ranked Priority test list.
  - Governing vs Superseded Invariants compliance checks.
  - Independent Change Decomposition & Modular PR split plan.
  - Code Ownership, Bus Factor, and Reviewer recommendations.
  - Concurrent In-Flight PR collision warnings.
- [ ] Unified 3-way projection switcher: Visual Analysis, Human Markdown (GFM), and Dense Agent JSON with token budget presets (Uncapped, 4k, 2k, 1k, 500) and recoverable omission markers (`[ref#<id>]`).

#### PH6-06: Evidence Navigation, Deep Links & Source Inspector
- [ ] Interactive source inspector modal: view real file content and syntax-highlighted line spans (`line_start` to `line_end`) directly within CodeAtlas.
- [ ] External GitHub deep links: direct URLs to commits, PRs (`html_url`), and issues on GitHub.
- [ ] Cross-artifact provenance breadcrumbs: trace claim &rarr; evidence &rarr; commit &rarr; PR &rarr; issue &rarr; ADR.
- [ ] Cross-tab navigation: 1-click jumps from investigation blast radius files into Component Explorer, Architecture Topology, and Evolution Timeline.

#### PH6-07: Unknowns, Risk & Confidence Presentation
- [ ] Visual Unknowns & Risk Alerts card: render `PreChangeBrief.unknowns` (unresolved dependencies, unindexed external libraries, missing test coverage, ambiguous queries).
- [ ] Model confidence scorecard: presentation of model reasoning confidence, evidence groundedness percentage, and budget telemetry (model calls, latency, tokens used).
- [ ] Missing evidence warnings: flag when a claim lacks supporting historical commits or AST references.
- [ ] Architectural role impact warnings: highlight when modified symbols are critical `entity` or `middleware` roles from Phase 5.

---

### Part B: SaaS Core, Multi-Tenancy & Platform Security

#### PH6-08: GitHub App Integration (OAuth, Webhooks & Installation Flow)
- [ ] GitHub App manifest configuration and OAuth web login flow.
- [ ] Webhook handlers: `installation`, `installation_repositories`, `push`, `pull_request`.
- [ ] Automatic repository synchronization upon GitHub App installation.
- [ ] Read-only repository access enforcement (ADR-002, AGENTS.md security rules).

#### PH6-09: Multi-Tenant Data Isolation & Authorization
- [ ] Database models: `Tenant`, `User`, `Organization`, `Membership` (roles: `owner`, `admin`, `member`, `viewer`).
- [ ] Enforce tenant boundary: add `tenant_id` foreign key and row-level authorization across all repository queries and investigations.
- [ ] API authentication middleware validating session JWTs and scoped repository permissions.
- [ ] Tenant data isolation integration tests ensuring zero cross-tenant data leakage.

#### PH6-10: Asynchronous Indexing Workers (Inngest / Background Jobs)
- [ ] Offload repository ingestion, AST parsing, Git history walks, and System One classification to async background workers.
- [ ] Inngest or Redis-backed task queue with job progress reporting and retry policies.
- [ ] WebSocket / Server-Sent Events (SSE) or polling endpoint for real-time indexing status (`queued`, `cloning`, `ast_parsing`, `history_indexing`, `complete`, `failed`).

#### PH6-11: Rate Limiting, Token Tracking & Cost Controls
- [ ] Per-tenant token budget enforcement and monthly spend tracking for LLM investigation calls.
- [ ] Rate limiting middleware on API endpoints (FastAPI Limiter / Redis token bucket).
- [ ] Usage dashboards & telemetry: token consumption, model calls, and cost accounting (<$0.05 per investigation target).

#### PH6-12: Caching Layer & Security Audit Logging
- [ ] Caching layer (Redis / in-memory cache) for frequent queries: architecture overviews, component topology, timeline summaries, and C4 exports.
- [ ] Security audit logging: persistent structured logs of repository access, investigation runs, secret scanning checks, and permission changes.
- [ ] Compliance verification ensuring no raw source code or credentials leak into logs or LLM context.

---

## Acceptance Criteria & Definition of Done

- [x] **PH6-01**: Repository overview computes 6 health dimensions and renders executive scorecard with hotspot files.
- [x] **PH6-02**: Component explorer provides interactive component directory, role filters, and coupling topology matrix.
- [x] **PH6-03**: Evolution timeline supports repository-wide and component-scoped views with monthly velocity and net churn.
- [ ] **PH6-04**: Developers can select investigation targets via interactive file/symbol tree, component picker, or open PRs without raw string typing.
- [ ] **PH6-05**: Pre-Change Investigation Brief interactive UI displays all Phase 4 & 5 synthesized intelligence with dual-format projections.
- [ ] **PH6-06**: Every evidence citation deep-links to GitHub or opens in the syntax-highlighted source code inspector.
- [ ] **PH6-07**: Unknowns, missing evidence, and confidence metrics are clearly presented in the visual brief.
- [ ] **PH6-08**: Users can authenticate via GitHub OAuth and install the read-only GitHub App.
- [ ] **PH6-09**: Tenant data is strictly isolated with server-side authorization enforcement.
- [ ] **PH6-10**: Repositories are indexed asynchronously with real-time progress reporting.
- [ ] **PH6-11**: Token usage, model costs, and rate limits are enforced per tenant.
- [ ] **PH6-12**: High-frequency queries are cached, and security audit logs record all repository operations.
- [ ] All unit, integration, and security tests pass.
