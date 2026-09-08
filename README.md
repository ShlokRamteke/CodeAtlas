# Project Archaeologist

> **Investigate software before you change it.**

Project Archaeologist is an AI-powered software change-investigation system.
It reconstructs the current codebase, its relationships, and its history so
developers can understand the consequences and constraints of a proposed
change before implementation.

## The Problem

When you inherit unfamiliar software, the important context is rarely in one
place. It is spread across source code, dependencies, tests, Git history, PRs,
issues, documentation, and architectural decisions.

Project Archaeologist connects these sources and turns them into a grounded
investigation.

## Core Workflow

```text
GitHub Repository
      ↓
Deterministic Code + History Analysis
      ↓
Project Knowledge
      ↓
Canonical ProjectContext + Project Graph (PostgreSQL)
      ↓
Change Investigation
      ↓
Evidence + Reasoning + Verification
      ↓
Pre-Change Investigation Brief
```

## Example

> “I want to replace Stripe in the payment service. What should I know before
> changing it?”

The system investigates affected code, callers, dependencies, tests, related
historical changes, PRs/issues, and other relevant evidence, then presents a
scoped brief with sources and unknowns.

## What It Understands

- current code structure and symbols
- imports, calls, dependencies, and relationships
- APIs and tests where detectable
- Git history and file evolution
- pull requests and issues
- documentation and engineering decisions
- historical and change-related evidence

## Main Experiences

- Repository Overview
- Architecture / Component Explorer
- Historical Timeline
- Change Investigation
- Pre-Change Investigation Brief
- Why Does This Exist?
- Evidence-backed answers
- MCP integration

## Initial Stack

- Next.js + TypeScript
- Python + FastAPI
- LangGraph + LiteLLM
- PostgreSQL + pgvector
- PostgreSQL relationship tables for the Project Graph
- Tree-sitter
- GitHub App
- MCP
- OpenTelemetry / Langfuse / Sentry
- Podman / Docker Compose multi-container local stack

## Development Context

- `AGENTS.md` — coding-agent development rules
- `PROJECT.md` — product intent and scope
- `ARCHITECTURE.md` — technical design
- `ROADMAP.md` — phase plan
- `STATUS.md` — current implementation state
- `DECISIONS.md` — significant decisions
- `phases/` — phase-specific goals and acceptance criteria

For coding-agent work, start with `AGENTS.md` and `STATUS.md`.

## Current Status

See [`STATUS.md`](file:///Users/shlok/Projects/Archelogiest/STATUS.md).

## License

TBD.
