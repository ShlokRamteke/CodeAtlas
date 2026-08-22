# Project Archaeologist

## Product Goal

Build an AI-powered SaaS that helps developers **understand unfamiliar
software before they change it**.

The product combines the current structure of a software system with the
history and engineering context that explain how it became what it is.

### Core Promise

> **Understand why your software became what it is.**

### Marketing Hook

> **Your code tells you what. We tell you why.**

The "why" is not limited to Git history. It is reconstructed from code,
relationships, commits, pull requests, issues, documentation, tests, and other
available engineering evidence.

---

## Problem

A developer joining or inheriting a software project can often determine what
the code does, but not why it has its current shape.

Important context is distributed across:

- source code,
- dependencies,
- APIs,
- tests,
- Git history,
- pull requests,
- issues,
- documentation,
- architectural decisions.

Answering a question like:

> "Why is this service designed this way?"

can require manually navigating many sources.

This becomes especially painful in:

- unfamiliar repositories,
- legacy systems,
- inherited projects,
- large codebases,
- services with long histories,
- code being modified by AI coding agents.

---

## Product Concept

Project Archaeologist builds a model of three things:

### 1. Current System

What exists today?

- architecture
- components
- APIs
- dependencies
- data flows
- tests

### 2. Historical Context

How did it get here?

- commits
- pull requests
- issues
- migrations
- major refactors
- feature evolution

### 3. Engineering Context

What surrounding information explains it?

- documentation
- architectural decisions
- tests
- constraints
- known issues
- related engineering artifacts

The AI investigation layer connects these sources to explain the system.

---

## Core User Questions

The product should answer four classes of questions.

### Understand

> How does checkout work?

> Which services handle authentication?

> What depends on PaymentService?

### Why

> Why does this workaround exist?

> Why was Redis introduced?

> Why is this API designed this way?

### History

> How did authentication evolve?

> What changed this service over the last two years?

> Which PR introduced this behavior?

### Before Change

> What should I know before modifying PaymentService?

> What historical decisions could affect this change?

> Which tests, services, and previous issues should I inspect?

---

## Core User Experience

### Repository Overview

Shows the current system:

- major components
- services
- dependencies
- APIs
- technologies

### Architecture Explorer

Lets developers navigate relationships between components.

### Historical Timeline

Shows significant changes and architectural evolution.

### Ask the Archaeologist

Natural-language investigation across code, relationships, history, and context.

### Why Does This Exist?

Signature investigation experience.

The system traces a component back through:

```text
Current Code
    ↓
Introducing Change
    ↓
PR
    ↓
Issue / Requirement
    ↓
Related Context
    ↓
AI Explanation
```

### Feature Archaeology

Reconstruct how a feature flows across the current system and how it evolved.

### Pre-Change Brief

Summarizes the current role, dependencies, historical context, known issues, and
relevant tests before a developer changes a component.

---

## MVP

### Repository

- GitHub App
- read-only access
- TypeScript/JavaScript support initially
- Git history
- pull requests
- issues
- documentation

### Project Intelligence

- AST/code analysis
- symbols
- dependencies
- architecture relationships
- embeddings
- hybrid retrieval

### Investigation

- current-state questions
- historical questions
- why questions
- pre-change context
- evidence citations
- confidence / uncertainty

### Product

- repository overview
- architecture explorer
- timeline
- investigation UI

### Agent Integration

- basic MCP server
- read-only archaeology tools

### Evaluation

- benchmark repository/data
- retrieval metrics
- groundedness/citation metrics
- token and latency tracking

---

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

---

## Differentiation

Project Archaeologist should not be positioned as:

- generic codebase chat,
- generic code search,
- generic Git history viewer,
- generic RAG chatbot.

Its differentiator is:

> **It connects what the software is today with the history and context that explain why it became that way.**

History is therefore both:

1. a major product capability, and
2. a strong marketing hook.

The broader product category is **AI software understanding**.

---

## Product Success

The MVP succeeds when a developer can take an unfamiliar repository and quickly answer:

1. What is this system?
2. How does this feature work?
3. Why is this component implemented this way?
4. How did it evolve?
5. What should I know before changing it?

without manually traversing code, Git history, PRs, issues, and documentation.
