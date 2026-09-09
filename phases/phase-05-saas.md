# Phase 5 — SaaS Experience & Core

## Goal

Turn the change-investigation engine into a clear, secure developer-facing web experience and multi-tenant SaaS product.

## Prerequisites

Phase 4 complete.

## Tasks

### SaaS Experience
- [ ] Repository overview and health indicators
- [ ] Architecture and component explorer
- [ ] Historical timeline and evolution view
- [ ] Change-investigation entry flow (target selection + proposed change input)
- [ ] Pre-Change Investigation Brief interactive UI
- [ ] Evidence navigation and source deep links
- [ ] Unknowns and confidence presentation

### SaaS Core & Security
- [ ] GitHub App integration (OAuth, webhooks, installation flow)
- [ ] Multi-tenant data isolation and authorization
- [ ] Asynchronous indexing worker (Inngest / background tasks)
- [ ] Rate limiting, token tracking, and cost controls
- [ ] User / team management and permissions
- [ ] Caching layer for frequent queries
- [ ] Audit logging for security and compliance

## Acceptance Criteria & Definition of Done

- [ ] A developer can select a target, describe a proposed change, run an investigation, and inspect the resulting evidence-backed brief through the web UI.
- [ ] Users can authenticate via GitHub and install the GitHub App.
- [ ] Repositories can be indexed asynchronously with progress reporting.
- [ ] Tenant data is strictly isolated.
- [ ] Token usage and costs are tracked per tenant.
- [ ] All unit/integration tests pass.
