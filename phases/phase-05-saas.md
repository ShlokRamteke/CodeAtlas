# Phase 5 — SaaS Core

## Goal

Turn the application into a secure, multi-tenant SaaS product.

## Prerequisites

Phase 4 complete.

## Tasks

- GitHub App integration (OAuth, webhooks, installation flow)
- Multi-tenant data isolation and authorization
- Asynchronous indexing worker (Inngest / background tasks)
- Rate limiting, token tracking, and cost controls
- User / team management and permissions
- Caching layer for frequent queries
- Audit logging for security and compliance

## Acceptance Criteria

- [ ] Users can authenticate via GitHub
- [ ] Repositories can be indexed asynchronously
- [ ] Tenant data is strictly isolated
- [ ] Token usage and costs are tracked per tenant
- [ ] All unit/integration tests pass
