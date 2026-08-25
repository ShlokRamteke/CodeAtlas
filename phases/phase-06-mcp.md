# Phase 6 — MCP Integration

## Goal

Expose Project Archaeologist capabilities to AI coding assistants via Model Context Protocol (MCP).

## Prerequisites

Phase 4 complete.

## Tasks

- Build MCP server using Python MCP SDK
- Expose read-only tools:
  - `why_does_this_exist(symbol_or_path)`
  - `get_pre_change_brief(component_or_file)`
  - `trace_feature(feature_name)`
  - `get_architecture(repository_id)`
  - `search_history(query)`
- Enforce read-only constraints and tenant authorization
- Package and document for Cursor, Claude Desktop, Windsurf

## Acceptance Criteria

- [ ] MCP tools can be invoked from Claude Desktop / Cursor
- [ ] Read-only guarantee is preserved
- [ ] Structured results match contracts
- [ ] All unit/integration tests pass
