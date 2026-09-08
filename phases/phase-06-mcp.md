# Phase 6 — MCP Integration

## Goal

Expose pre-change investigation and software archaeology capabilities to AI coding assistants via the Model Context Protocol (MCP).

## Prerequisites

Phase 4 complete.

## Tasks

- [ ] Build MCP server using Python MCP SDK
- [ ] Expose read-only investigation tools:
  - `investigate_change(target, proposed_change)` — run pre-change investigation and return structured brief
  - `get_change_context(target)` — get scoped dependency, test, and constraint context for a target
  - `get_dependencies(entity_id)` — query callers and dependencies
  - `trace_feature(feature_name)` — trace feature evolution across code and history
  - `search_history(query)` — deterministic multi-attribute historical search
  - `get_related_issues(symbol_or_path)` — retrieve linked PRs, issues, and discussions
  - `why_does_this_exist(symbol_or_path)` — focused investigation on why code exists
- [ ] Enforce read-only constraints and tenant authorization
- [ ] Return compact, token-efficient, evidence-backed responses
- [ ] Package and document for Cursor, Claude Desktop, Windsurf

## Acceptance Criteria & Definition of Done

- [ ] An MCP client can request change context or an investigation and receive a scoped, evidence-backed result using the same authorization boundary as the web API.
- [ ] Read-only guarantee is preserved.
- [ ] Structured results match contracts.
- [ ] All unit/integration tests pass.
