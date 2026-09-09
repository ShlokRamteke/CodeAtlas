# Development Status

## Current Phase

Phase 3 — Historical + Engineering Context

## Current Task

PH3-04 Complete &mdash; Next: PH3-05 (Enrich ProjectContext)

## Status

IN PROGRESS

## Product Focus

Project Archaeologist is centered on **Pre-Change Investigation**. The product
uses current code, relationships, history, and engineering evidence to help a
developer understand a proposed change before implementation.

## Completed

- **Phase 1 — Foundation**: Complete foundation (Postgres, Alembic, FastAPI, Contracts, Next.js).
- **Phase 2 — Repository Understanding**: Complete current-system layer (Tree-sitter AST, relationships, Context Builder, canonical `ProjectContext`).
- **Clean-Room Reference Architecture & Licensing Assessment**:
  - Analyzed external reference architecture in an isolated, untracked local quarantine (`_references/` in `.gitignore`).
  - Formulated **ADR-016 (Clean-Room Intellectual Property Boundary & Licensing Policy)**: Enforced strict clean-room isolation against AGPL-3.0 contamination, guaranteeing Project Archaeologist remains 100% MIT permissive with zero code, schema, prompt, or test copying.
  - Formulated **ADR-017 (Quantitative Change Risk, Historical Co-Change, and Guarding Test Reachability)**: Adopted published peer-reviewed algorithms (Kamei et al. Just-in-Time defect prediction with Shannon churn entropy, historical co-change hidden coupling detection, reach-ranked guarding test signals, and token-budgeted output distillation).
  - Implemented and verified clean-room algorithms in `app.history.change_risk`, `app.history.co_change`, and `app.history.guarding_tests`.
  - 100% automated test pass rate across 52 unit/integration tests (11 new tests added covering Kamei metrics, Shannon entropy, defect pressure decay, co-change partner mining, hidden coupling warnings, reach ranking, untested changes, and stale test detection).
  - Updated live documentation across `ARCHITECTURE.md`, `DECISIONS.md`, `README.md`, and `phases/phase-04-change-investigation.md`.
- **Phase 3 — Task PH3-01 (Git History Indexing)**:
  - Database model `CommitFileChange` (`ChangeType`: added, modified, deleted, renamed) and `0003_add_commit_file_changes` migration.
  - `GitHistoryIndexer` service calculating file history and identifying the **introducing commit** (origin commit) for any file or component.
  - `GitHubRepoFetcher.fetch_public_repo_commits()` extracting real commit history and file diffs.
  - REST endpoints: `GET /api/v1/repositories/{id}/commits`, `GET /api/v1/repositories/{id}/files/{path}/history`, `GET /api/v1/repositories/{id}/components/{path}/history`, and `POST /commits/ingest`.
  - Frontend interactive **Git History** tab and **File Evolution Inspector** in Next.js UI.
  - 100% automated test pass rate (19/19 pytest tests).
- **Phase 3 — Task PH3-02 (Commit &rarr; PR &rarr; Issue Linking)**:
  - Deterministic regex parser `ReferenceExtractor` extracting PR merge/squash/mention patterns and Issue closing/reference patterns (`Fixes #123`, `Merge pull request #45`, `PR #45`, `GH-101`, `resolves #99`).
  - Database models `CommitPullRequestLink`, `CommitIssueLink`, `PullRequestIssueLink`, enhanced `PullRequest` and `Issue` schemas with labels and closed timestamps, and `0004_add_pr_issue_links` migration.
  - `HistoricalLinker` service indexing PRs and Issues, linking commits upon ingestion, resolving unlinked references, and generating end-to-end `Code -> Commit -> PR -> Issue` provenance traces.
  - `GitHubRepoFetcher` enhanced to fetch PR and Issue metadata from the GitHub REST API.
  - REST endpoints: `GET /api/v1/repositories/{id}/pull-requests`, `GET /api/v1/repositories/{id}/issues`, `GET /api/v1/repositories/{id}/trace/{file_path:path}`, and ingestion endpoints.
  - Frontend interactive **Historical Traceability & Artifact Linking** sub-views in Next.js UI with live cross-referenced chips on commits, PRs, and issues.
  - 100% automated test pass rate (31/31 pytest tests, clean frontend build & contracts typecheck).
- **Phase 3 — Task PH3-03 (Historical Retrieval)**:
  - `HistoricalRetriever` service enabling multi-dimensional searching across commits (message, author, touched path, date ranges), PRs (keyword, state, author, label), and issues (keyword, state, author, label).
  - Symbol history extraction identifying the introducing commit, file path, line span, and chronological evolutionary milestones for any code symbol.
  - Multi-artifact deterministic evidence synthesis ranking `HistoricalEvidenceRecord` items with query relevance score, recency, confidence metrics, and citation links without LLM calls.
  - REST endpoints: `GET /api/v1/repositories/{id}/history/search`, `POST /api/v1/repositories/{id}/history/retrieve`, and `GET /api/v1/repositories/{id}/symbols/{name}/history`.
  - Frontend interactive **Deterministic Search & Evidence** explorer in Next.js UI with live keyword querying, multi-attribute filter chips, symbol evolution timeline inspector, and ranked evidence cards.
  - 100% automated test pass rate (32/32 pytest tests, clean frontend build & contracts typecheck).
- **Phase 3 — Task PH3-04 (Engineering Context)**:
  - `EngineeringContextParser` parsing Markdown headings, sections, ADR statuses/deciders, and extracting RFC 2119 design constraints and architectural invariants into Security, Architecture, Performance, Testing, and Data Integrity domains without LLM calls.
  - Database models `EngineeringDocument` and `DesignConstraint` with Alembic migration `0005_add_engineering_context`.
  - `EngineeringContextIndexer` service ingesting repository documentation, indexing ADRs, querying design constraints, and performing deterministic context searches.
  - REST endpoints: `GET /api/v1/repositories/{id}/engineering/overview`, `GET /docs`, `GET /docs/{doc_id}`, `GET /adrs`, `GET /constraints`, `GET /search`, and `POST /ingest`.
  - Frontend interactive **Engineering Context** tab & `EngineeringContextViewer` component in Next.js UI with ADR cards, design constraints matrix, document catalog, and real-time context search.
  - 100% automated test pass rate (39/39 pytest tests, clean frontend build & contracts typecheck).

## Remaining

- **PH3-05**: Enrich ProjectContext (extend canonical ProjectContext with historical changes, PRs, issues, ADRs, and design constraints)
- **PH3-06**: Historical Timeline / Developer View

## Blockers

None known.

## Next Action

Start Task PH3-05: Enrich ProjectContext (extend canonical ProjectContext with historical changes, PRs, issues, ADRs, and design constraints, preserving provenance for downstream change investigation).

## Session Rule

Update this file after meaningful development sessions. If work is incomplete,
keep the task in progress, record blockers, and set the next actionable step.

Do not advance phases until the current phase definition of done is satisfied.

## Architecture Principle

There is one canonical `ProjectContext`. Current-system, historical, and
engineering evidence enrich the same model. Human UI and AI/agent consumers
receive scoped views of that model.

## Last Updated

2026-09-08
