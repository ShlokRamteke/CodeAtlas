# Development Status

## Current Phase

Phase 3 — Historical + Engineering Context

## Current Task

PH3-02 Complete &mdash; Next: PH3-03 (Historical Retrieval)

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
  - 100% automated test pass rate (29/29 pytest tests, clean frontend build).

## Remaining

- **PH3-03**: Historical Retrieval
- **PH3-04**: Engineering Context
- **PH3-05**: Enrich ProjectContext
- **PH3-06**: Historical Timeline / Developer View

## Blockers

None

## Next Action

Start Task PH3-03: Implement Deterministic Historical Retrieval (commit message/author/path filters, PR/issue keyword search, component-scoped historical evidence query without LLMs).


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
