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

## UI/UX & Accessibility Guiding Principles

To avoid cognitive overload, feature bloat, and visual noise, the CodeAtlas UI strictly adheres to progressive disclosure and accessibility:

1. **Progressive Disclosure over Metric Dumps**:
   - **Primary View = Actionable Answers**: Immediate visibility for *What breaks? (Blast Radius)*, *What is the risk level? (Risk Tier)*, *Which invariants govern this?*, and *Which guarding tests must run?*.
   - **Secondary View = On-Demand Math & Telemetry**: Deep statistical formulas (Kamei $LA, LD, NF, ND, NS, H(P)$, deep-walk defect pressure, coupling adjacency matrices, raw AST node trees) are tucked behind collapsible sections, detail drawers, and inspection modals.
2. **Cognitive Ergonomics & Scannability**:
   - Card-based visual hierarchy with high-signal badge summaries.
   - Clean color coding with semantic fallback: Emerald (guarded/low risk), Amber (moderate/warning), Rose (high risk/untested/invariant violation), Indigo (architecture/system role).
   - Never rely on color alone: every status indicator pairs color with an icon and unambiguous text label.
3. **Accessibility (WCAG AA & Keyboard-First)**:
   - Full keyboard navigation for interactive widgets (focus rings, `Tab`/`Shift+Tab` flow, `Enter`/`Space` activation, `Esc` modal dismiss).
   - Semantic HTML and ARIA landmarks (`role="tablist"`, `role="dialog"`, `aria-expanded`, `aria-label`).
   - High-contrast text palettes (`text-slate-900 dark:text-slate-100` on calibrated surfaces) meeting WCAG AA contrast thresholds.
4. **Focused Investigation Journey (No Generic Chat Bloat)**:
   - Dedicated, step-by-step developer journey: **Select Target &rarr; Choose Intent &rarr; Review Synthesized Brief &rarr; Run Guarding Tests &rarr; Export Projections**.
   - No unsolicited chatbot sidebars, unstructured repository chat prompts, or uncurated node spaghetti graphs that dilute the developer's goal.

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
- [ ] Accessible, keyboard-navigable target selector with fuzzy autocomplete over Phase 2 Tree-sitter AST files and symbols (replaces raw manual string typing).
- [ ] Component-scoped selector: 1-click component picking auto-populates canonical target files without manual path hunting.
- [ ] In-flight PR selector: accessible dropdown linking open PRs and branch targets with live concurrent collision badges.
- [ ] Intent templates: 1-click presets ("Refactor API", "Schema Migration", "Bug Fix", "Add Endpoint") for instant query framing.
- [ ] Pre-flight impact preview: instant blast radius & risk summary before launching the model pipeline, avoiding unnecessary runs.

#### PH6-05: Pre-Change Investigation Brief Interactive UI
- [ ] Executive decision header: 4 high-signal summary tiles (Blast Radius size, Quantitative Risk Tier, Invariants at Risk, Guarding Tests Count).
- [ ] Progressive disclosure layout:
  - **Primary**: Scannable blueprint (action items, affected callers, test priorities, invariant warnings).
  - **Secondary (Expandable Drawers)**: Kamei mathematical breakdown ($LA, LD, NF, ND, NS, H(P)$), Shannon churn entropy, and Modular PR split decomposition.
- [ ] Ownership & reviewer cards with maintainer role badges and contact metadata.
- [ ] Accessible 3-way projection switcher (Visual Analysis, Human Markdown GFM, Dense Agent JSON) with 1-click token budget presets (Uncapped, 4k, 2k, 1k, 500) and copy controls.

#### PH6-06: Evidence Navigation, Deep Links & Source Inspector
- [ ] Accessible source inspector modal: syntax-highlighted code with line numbers, breadcrumbs, and `Esc` keyboard dismiss.
- [ ] External GitHub deep links with visual external-link icons and descriptive `aria-label`s for screen readers.
- [ ] Compact provenance trace pills: claim &rarr; evidence &rarr; commit &rarr; PR &rarr; issue &rarr; ADR.
- [ ] Cross-tab shortcuts: 1-click jumps from blast-radius files into Component Explorer, Architecture Topology, and Evolution Timeline.

#### PH6-07: Unknowns, Risk & Confidence Presentation
- [ ] High-contrast, dismissible Unknowns & Risk Alerts card: clear callouts for unindexed dependencies, ambiguous queries, and missing test coverage.
- [ ] Accessible model confidence meter: dual visual progress bar and numerical percentage with groundedness rating.
- [ ] Architectural role impact warning badges: contextual alerts when modifying high-risk `entity` or `middleware` components.
- [ ] Missing evidence warnings: prominent visual badges when assertions lack historical commit or AST backing.

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
- [ ] **PH6-04**: Developers can select investigation targets via accessible autocomplete dropdown, component picker, or open PRs without raw manual typing.
- [ ] **PH6-05**: Pre-Change Investigation Brief interactive UI presents actionable conclusions first (blast radius, risk tier, guarding tests, broken invariants) with deep statistical math (Kamei metrics, Shannon entropy, split decomposition) accessible via progressive disclosure drawers.
- [ ] **PH6-06**: Every evidence citation deep-links to GitHub or opens in the syntax-highlighted source code inspector with keyboard navigation (`Esc` dismiss).
- [ ] **PH6-07**: Unknowns, missing evidence, and confidence metrics are clearly presented with high-contrast alert badges and clear remediation guidance.
- [ ] **PH6-08**: Users can authenticate via GitHub OAuth and install the read-only GitHub App.
- [ ] **PH6-09**: Tenant data is strictly isolated with server-side authorization enforcement.
- [ ] **PH6-10**: Repositories are indexed asynchronously with real-time progress reporting.
- [ ] **PH6-11**: Token usage, model costs, and rate limits are enforced per tenant.
- [ ] **PH6-12**: High-frequency queries are cached, and security audit logs record all repository operations.
- [ ] All unit, integration, and security tests pass.
