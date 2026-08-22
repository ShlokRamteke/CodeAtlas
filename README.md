# Project Archaeologist

> **Understand why your software became what it is.**

Your code tells you **what** the system does.  
Your Git history tells you **what changed**.  
**Project Archaeologist helps explain why.**

Project Archaeologist is an AI-powered SaaS for understanding unfamiliar
software by combining the system's current architecture with its historical and
engineering context.

## What It Understands

```text
Current System
├── Code
├── Components
├── APIs
├── Dependencies
└── Tests

Historical Context
├── Commits
├── Pull Requests
├── Issues
└── Evolution

Engineering Context
├── Documentation
├── Decisions
└── Constraints
```

The system connects these sources and uses AI to investigate questions such as:

- How does checkout work across the system?
- Why does this workaround exist?
- How did authentication evolve?
- What historical context should I know before changing this service?
- Which previous decisions or issues explain this architecture?

## Core Experience

### Understand
See how the system works today.

### History
See how the system became what it is.

### Explain
Use AI to connect current behavior with historical evidence and explain why.

### Before You Change
Get a compact engineering brief before modifying unfamiliar code.

## Core Workflow

```text
GitHub Repository
      ↓
Deterministic Analysis
      ↓
Project Intelligence
      ├── Current System
      ├── Historical Context
      └── Engineering Context
      ↓
Hybrid Retrieval
      ↓
Archaeological Investigation
      ↓
Evidence Verification
      ↓
Answer + Sources
```

## Initial Stack

- Next.js + TypeScript
- Python + FastAPI
- LangGraph
- PostgreSQL + pgvector
- Tree-sitter
- GitHub App
- MCP
- OpenTelemetry / Langfuse

## Main Features

- Repository Overview
- Architecture Explorer
- Historical Timeline
- Ask the Archaeologist
- Why Does This Exist?
- Feature Archaeology
- Pre-Change Brief
- Evidence-backed answers
- MCP integration

## Product Positioning

Project Archaeologist is **not** a generic "chat with your codebase" product.

It combines:

> **Current system understanding + history + engineering context + AI reasoning**

History is a key differentiator, but the product goal is broader:

> **Help developers understand unfamiliar software before they change it.**

## Development Context

- `AGENTS.md` — how coding agents should work
- `PROJECT.md` — product intent and scope
- `ARCHITECTURE.md` — current technical design
- `ROADMAP.md` — phase-level development plan
- `STATUS.md` — current implementation state
- `DECISIONS.md` — significant technical decisions
- `phases/` — phase goals and acceptance criteria
- `.agents/workflows/` — optional Antigravity workflows

For coding-agent work, start with `AGENTS.md` and `STATUS.md`.

## Current Status

See `STATUS.md`.

## License

TBD.


## Development Workflows

For Antigravity, optional workflows can live under `.agents/workflows/`.
These workflows operate on the same project source of truth and should not
duplicate product or architecture documentation.

Suggested workflows:
- `start-task`
- `finish-task`
- `architecture-change`
