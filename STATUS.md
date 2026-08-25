# Development Status

## Current Phase

Phase 3 — Historical + Engineering Context

## Current Task

PH3-01 Complete &mdash; Next: PH3-02 (Commit &rarr; PR &rarr; Issue Linking)

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

## Remaining

- **PH3-02**: Commit &rarr; PR &rarr; Issue Linking
- **PH3-03**: Historical Retrieval
- **PH3-04**: Engineering Context
- **PH3-05**: Enrich ProjectContext
- **PH3-06**: Historical Timeline / Developer View

## Blockers

None

## Next Action

Start Task PH3-02: Implement Commit &rarr; PR &rarr; Issue linking and reference extraction.


## Session Rule

Update this file after meaningful development sessions.

If work is incomplete:
- keep the task in progress,
- list remaining work,
- record blockers,
- set the next actionable step.

Do not advance phases until the current phase definition of done is satisfied.

## Last Updated

2026-08-22
