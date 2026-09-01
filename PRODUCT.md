# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
- Developers and engineers exploring public repositories in an engaging, intuitive way to understand project growth, milestones, and architectural decisions.
- Software engineers onboarding to unfamiliar codebases or taking over legacy code who need to understand how the system evolved and why specific trade-offs were made.
- Senior engineers and developers preparing for refactors or modifications who need reliable context on why implementations exist before changing them.

## Product Purpose
Project Archaeologist is an AI-powered software intelligence platform that helps developers understand why software became what it is. It reconstructs deep codebase context by uniting current structural architecture (AST, symbols, dependency graphs) with historical provenance (commits, PRs, issues) and engineering context (design decisions, tests). Success means a developer can explore any repository, trace any component back to its origins and driving decisions, and prepare changes with total confidence.

## Positioning
"Your code tells you what. We tell you why."
Unlike generic codebase chat, code search tools, or basic Git history viewers, Project Archaeologist deterministically connects current system structure to the historical and engineering context that explains why it was built that way.

## Operating Context
- Web dashboard and interactive visual explorer connected to GitHub repositories.
- Workflows: Repository onboarding, architectural exploration, historical timeline inspection, component provenance tracing, and pre-change impact briefings.
- Technical environment: Next.js 14 frontend (Tailwind CSS, TypeScript), FastAPI backend, PostgreSQL with pgvector, containerized with Compose / Podman.

## Capabilities and Constraints
- Capabilities:
  - Architecture Explorer: AST parsing, symbol extraction, dependency graph, and uncertainty detection.
  - Historical Traceability: Commit, PR, and Issue cross-referencing, origin commit discovery, and multi-tier provenance traces.
  - Ask the Archaeologist & Why Does This Exist?: Evidence-backed answers to architectural and historical questions.
  - Unified Context: Deterministic ProjectContext shared across human visualization and AI reasoning pipelines.
- Constraints:
  - Read-only GitHub access for MVP (no autonomous code modification or PR generation).
  - Deterministic indexing before AI reasoning.
  - Secret scanning and repository tenant isolation.

## Brand Commitments
- Name: Project Archaeologist / Archaeologist
- Brand Personality & Visual Tone: Modern enterprise SaaS — clean, minimal, polished dashboard with high-density data visualization and refined analytics aesthetic.
- Narrative Hook: "Your code tells you what. We tell you why."

## Evidence on Hand
- Full repository architecture and phase specifications ([PROJECT.md](file:///Users/shlok/Projects/Archelogiest/PROJECT.md), [ARCHITECTURE.md](file:///Users/shlok/Projects/Archelogiest/ARCHITECTURE.md), [ROADMAP.md](file:///Users/shlok/Projects/Archelogiest/ROADMAP.md), [STATUS.md](file:///Users/shlok/Projects/Archelogiest/STATUS.md), [DECISIONS.md](file:///Users/shlok/Projects/Archelogiest/DECISIONS.md)).
- Working FastAPI backend (`backend/app/`) with Tree-sitter AST parser, Git history indexer, and HistoricalLinker.
- Working Next.js 14 frontend (`frontend/src/`) with Architecture Explorer and Historical Traceability views.

## Product Principles
1. **Explain the Why, Not Just the What**: Always bridge today's code structure with the historical decisions and discussions that produced it.
2. **Deterministic Truth Before AI Reasoning**: Index facts deterministically (AST, regex linkers, Git graphs) before passing compact context to LLMs.
3. **Engaging Exploration with Analytical Depth**: Make discovering project history and architecture fun and accessible while providing rigorous provenance.
4. **Unified Truth Across Humans & Models**: Single canonical `ProjectContext` ensures that UI visualizers and AI agents inspect the exact same grounding data.

## Accessibility & Inclusion
- WCAG AA compliant contrast ratios, accessible data visualizations, keyboard navigation across timeline and graph explorers, and semantic HTML structure.
