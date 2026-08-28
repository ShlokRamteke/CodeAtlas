# Project Archaeologist

## Product Goal

Build an AI-powered SaaS that helps developers **understand unfamiliar software before they change it**.

The product combines the current structure of a software system with the history and engineering context that explain how it became what it is.

### Core Promise

> Understand why your software became what it is.

### Marketing Hook

> Your code tells you what. We tell you why.

The "why" is not limited to Git history. It is reconstructed from code, relationships, commits, pull requests, issues, documentation, tests, and other engineering evidence.

## Problem

A developer joining or inheriting a software project can often determine what the code does, but not why it has its current shape.

Important context is distributed across source code, dependencies, APIs, tests, Git history, pull requests, issues, documentation, and architectural decisions.

## Product Understanding Model

Project Archaeologist builds Project Intelligence in three layers:

### 1. Current System

What exists today:
- architecture
- components
- APIs
- dependencies
- data flows
- tests
- symbols and relationships
- confidence/provenance for inferred relationships

The first implementation goal is not perfect code understanding. It is a reliable current-system context layer that can support humans, retrieval, and later AI reasoning.

### 2. Historical Context

How did it get here:
- commits
- pull requests
- issues
- migrations
- major refactors
- feature evolution

### 3. Engineering Context

What surrounding information explains it:
- documentation
- architecture decisions
- tests
- known issues
- constraints
- related engineering artifacts

## Core User Questions

### Understand
- How does checkout work?
- Which services handle authentication?
- What depends on PaymentService?

### Why
- Why does this workaround exist?
- Why was Redis introduced?
- Why is this API designed this way?

### History
- How did authentication evolve?
- What changed this service?
- Which PR introduced this behavior?

### Before Change
- What should I know before modifying PaymentService?
- What historical decisions could affect this change?
- Which tests, services, and previous issues should I inspect?

## Core User Experience

- Repository Overview
- Architecture Explorer
- Historical Timeline
- Ask the Archaeologist
- Why Does This Exist?
- Feature Archaeology
- Pre-Change Brief
- Evidence-backed answers

## MVP

- GitHub repository connection
- TypeScript/JavaScript support initially
- deterministic code/dependency indexing
- current-system context
- Git history
- pull requests/issues/docs
- hybrid retrieval
- architecture overview
- historical timeline
- Ask the Archaeologist
- Why Does This Exist?
- evidence citations
- basic MCP server
- evaluation benchmark
- token/cost tracking

## Non-Goals for MVP

- autonomous code changes
- automatic PR creation
- generic coding agent
- Slack/Jira integrations
- production monitoring
- broad multi-language support
- enterprise infrastructure
- large autonomous agent swarms
- repository code execution

## Differentiation

The product is not:
- generic codebase chat
- generic code search
- generic Git history viewer
- generic RAG

Its differentiator is:

> It connects what the software is today with the history and engineering context that explain why it became that way.

History is a major capability and marketing hook; AI software understanding is the broader product category.
