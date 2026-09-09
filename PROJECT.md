# CodeAtlas

## Goal

Build an AI-powered SaaS for **pre-change software investigation**: help
developers understand what they are about to change, why the relevant code
exists, how it evolved, what depends on it, and what consequences or hidden
constraints should be considered before implementation.

## Core Promise

> Investigate software before you change it.

## Product Positioning

CodeAtlas is an **AI change-investigation system**, not a generic
codebase chat product. Its primary job is to assemble evidence about a
proposed change and turn that evidence into a grounded investigation brief.

The product uses software archaeology as its underlying intelligence: current
code + relationships + history + engineering evidence.

## Problem

When developers modify unfamiliar software, the important context is usually
distributed across:

- source code,
- dependencies and call relationships,
- tests,
- Git history,
- pull requests,
- issues,
- documentation,
- architectural decisions,
- patterns of related change.

Code search can usually explain what exists. The harder problem is determining
what will be affected by a change, why the current implementation exists, and
which historical or engineering constraints are easy to miss.

## Core Experience

A developer provides a target and a proposed change, for example:

> Replace the Stripe integration with another payment provider.

CodeAtlas investigates the repository and produces a **Change
Investigation Brief** covering:

- change scope,
- affected components,
- dependency and call paths,
- relevant tests,
- historical context,
- related PRs/issues,
- historical failures or reversions where discoverable,
- hidden coupling or co-change signals,
- known constraints,
- important unknowns,
- evidence and source locations,
- recommended areas to inspect before implementation.

## Core Questions

- What will this change touch?
- What depends on the code I am changing?
- Why is the current implementation this way?
- How did this component evolve?
- What constraints were introduced by earlier changes?
- What should I inspect before implementing the change?

## Intelligence Model

The system has one canonical `ProjectContext`. It is enriched over time:

1. **Current System Context** — what the code is and how it is connected today.
2. **Historical Context** — how the relevant code and relationships evolved.
3. **Engineering Context** — tests, docs, issues, decisions, and other evidence.

The Investigation Engine reasons over a scoped slice of this same context.
There is no separate human-context and LLM-context knowledge base.

## Core Product Experiences

1. Repository Overview
2. Component / Architecture Exploration
3. Historical Timeline
4. Change Investigation
5. Pre-Change Investigation Brief
6. Why Does This Exist?
7. Evidence-backed investigation
8. MCP access for coding agents

General repository Q&A may exist as supporting functionality, but it is not
the primary product experience.

## MVP

- GitHub repository connection
- TypeScript/JavaScript and Python support
- deterministic current-system/code analysis
- Project Graph backed by PostgreSQL relationship tables
- Git history
- pull requests/issues/docs where accessible
- hybrid retrieval
- historical and relationship retrieval
- bounded Investigation Engine
- Pre-Change Investigation Brief
- evidence citations
- basic MCP server
- evaluation benchmark for change-investigation tasks
- token/cost and latency tracking

## Non-Goals for MVP

- autonomous code changes
- automatic PR creation
- generic coding-agent replacement
- Slack/Jira integrations
- production monitoring
- broad multi-language support
- enterprise infrastructure
- large autonomous agent swarms
- repository code execution

## Differentiation Principle

Do not compete on generic repository chat, code search, graph visualization,
Git analytics, or MCP availability. These are enabling capabilities.

The product is differentiated by the **workflow**:

> Given a proposed software change, investigate the current system, its
> evolution, and its evidence before a developer touches the code.
