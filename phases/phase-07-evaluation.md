# Phase 7 — Evaluation & Production Hardening

## Goal

Measure whether Project Archaeologist reliably improves pre-change understanding, validate investigation accuracy and groundedness, and harden the system for production use.

## Prerequisites

Core MVP workflow complete (Phases 1–6).

## Tasks

- [ ] Golden benchmark repositories and versioned change-investigation test dataset
- [ ] Affected-component recall evaluation (measuring blast-radius detection)
- [ ] Dependency and impact recall evaluation
- [ ] Historical retrieval and evidence accuracy evaluation
- [ ] Citation accuracy and groundedness evaluation (hallucination prevention)
- [ ] Investigation completeness and claim accuracy scoring
- [ ] Token usage, model costs, and latency tracking per investigation
- [ ] Observability (OpenTelemetry, Langfuse, Sentry)
- [ ] Security and authorization boundary audit
- [ ] Production performance tuning and operational playbooks

## Acceptance Criteria & Definition of Done

- [ ] The benchmark is repeatable, investigation quality is measurable, and model usage is tracked.
- [ ] Groundedness score meets target (>95% verified citations).
- [ ] Token usage stays within budget (<$0.05 per standard investigation).
- [ ] Latency meets SLO (<5s for standard investigation retrieval and synthesis).
- [ ] All security checks and permission boundaries pass.
- [ ] Core workflow is stable and hardened for real use.
