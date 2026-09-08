# Development Status

## Current Phase

Phase 3 — Historical + Engineering Context

## Current Task

PH3-04 Complete &mdash; Next: PH3-05 (Enrich ProjectContext)

## Status


IN PROGRESS

## Product Focus

The product goal is to help developers understand unfamiliar software.

History is a major differentiator and marketing hook, but not the entire
product. The core system combines current architecture, historical context,
engineering context, and AI reasoning.

## Completed

- **Phase 1 — Foundation**: Complete foundation (Postgres, Alembic, FastAPI, Contracts, Next.js).
- **Phase 2 — Repository Understanding**: Complete current-system layer (Tree-sitter AST, relationships, Context Builder, unified `ProjectContext`).
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

- **PH3-05**: Enrich ProjectContext
- **PH3-06**: Historical Timeline / Developer View

## Blockers

None

## Next Action

Start Task PH3-05: Enrich ProjectContext (extend unified ProjectContext with historical changes, PRs, issues, ADRs, and design constraints).



## Session Rule

Update this file after meaningful development sessions.

If work is incomplete:
- keep the task in progress,
- list remaining work,
- record blockers,
- set the next actionable step.

Do not advance phases until the current phase definition of done is satisfied.

## Last Updated

2026-08-28
