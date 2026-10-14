from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.history.engineering_indexer import EngineeringContextIndexer
from app.history.git_indexer import (
    ChangeType,
    GitHistoryIndexer,
    ParsedCommit,
    ParsedFileChange,
)
from app.history.historical_linker import (
    HistoricalLinker,
    ParsedIssue,
    ParsedPullRequest,
)
from app.models.repository import Repository


@pytest.mark.asyncio
async def test_repository_wide_evolution_timeline(db_session: AsyncSession) -> None:
    # 1. Create Repository
    repo = Repository(
        id=uuid.uuid4(),
        owner="timeline-saas",
        name="evolution-repo",
        full_name="timeline-saas/evolution-repo",
        default_branch="main",
    )
    db_session.add(repo)
    await db_session.commit()

    # 2. Add ADRs
    eng_indexer = EngineeringContextIndexer(db_session)
    await eng_indexer.index_document(
        repository_id=repo.id,
        path="docs/adr/0001-cqrs-event-sourcing.md",
        raw_content="""# ADR 0001: Implement CQRS for core domain

## Status
Accepted

## Context
We need scalable write-read segregation.

## Decision
All state transitions MUST publish domain events.
""",
    )
    await db_session.commit()

    # 3. Add PRs and Issues
    linker = HistoricalLinker()
    prs = [
        ParsedPullRequest(
            number=10,
            title="feat(checkout): add order processing pipeline",
            body="Implements checkout flow. Fixes #20",
            state="merged",
            author="alice",
            merged_at=datetime(2025, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
            labels=["core"],
            html_url="https://github.com/timeline-saas/evolution-repo/pull/10",
        )
    ]
    await linker.index_pull_requests(repo.id, prs, db_session)

    issues = [
        ParsedIssue(
            number=20,
            title="Checkout race condition bug",
            body="Orders duplicate on double submit",
            state="closed",
            author="tester",
            closed_at=datetime(2025, 2, 12, 9, 0, 0, tzinfo=timezone.utc),
            labels=["bug"],
            html_url="https://github.com/timeline-saas/evolution-repo/issues/20",
        )
    ]
    await linker.index_issues(repo.id, issues, db_session)

    # 4. Ingest sequence of commits across multiple components
    indexer = GitHistoryIndexer()
    commits = [
        # Intro
        ParsedCommit(
            commit_hash="a100000000000000000000000000000000000001",
            author_name="Alice Dev",
            author_email="alice@example.com",
            committed_at=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            message="Initial repository setup",
            file_changes=[
                ParsedFileChange(
                    file_path="README.md",
                    change_type=ChangeType.ADDED,
                    insertions=20,
                    deletions=0,
                ),
                ParsedFileChange(
                    file_path="src/index.ts",
                    change_type=ChangeType.ADDED,
                    insertions=50,
                    deletions=0,
                ),
            ],
        ),
        # Feature addition
        ParsedCommit(
            commit_hash="b200000000000000000000000000000000000002",
            author_name="Alice Dev",
            author_email="alice@example.com",
            committed_at=datetime(2025, 1, 15, 14, 0, 0, tzinfo=timezone.utc),
            message="feat(checkout): add order processing pipeline (#10)",
            file_changes=[
                ParsedFileChange(
                    file_path="src/checkout/service.ts",
                    change_type=ChangeType.ADDED,
                    insertions=120,
                    deletions=0,
                ),
            ],
        ),
        # Bug fix
        ParsedCommit(
            commit_hash="c300000000000000000000000000000000000003",
            author_name="Bob Fixer",
            author_email="bob@example.com",
            committed_at=datetime(2025, 2, 5, 11, 0, 0, tzinfo=timezone.utc),
            message="fix(checkout): resolve idempotency race condition in orders (Fixes #20)",
            file_changes=[
                ParsedFileChange(
                    file_path="src/checkout/service.ts",
                    change_type=ChangeType.MODIFIED,
                    insertions=15,
                    deletions=5,
                ),
            ],
        ),
        # Refactor
        ParsedCommit(
            commit_hash="d400000000000000000000000000000000000004",
            author_name="Charlie Refactor",
            author_email="charlie@example.com",
            committed_at=datetime(2025, 3, 1, 16, 0, 0, tzinfo=timezone.utc),
            message="refactor(core): simplify handler routing and consolidate types",
            file_changes=[
                ParsedFileChange(
                    file_path="src/index.ts",
                    change_type=ChangeType.MODIFIED,
                    insertions=10,
                    deletions=30,
                ),
            ],
        ),
    ]

    await indexer.index_commits(repo.id, commits, db_session)

    # 5. Retrieve Repository-Wide Timeline (component_path="all")
    timeline = await indexer.get_component_timeline(repo.id, "all", db_session)

    assert timeline["repository_id"] == repo.id
    assert timeline["component_path"] == "all"
    assert timeline["total_events"] >= 5  # 4 commits + 1 ADR

    # Verify event types present
    event_types = {m["event_type"] for m in timeline["milestones"]}
    assert "introduction" in event_types
    assert "feature_addition" in event_types
    assert "bug_fix" in event_types
    assert "refactor" in event_types
    assert "architectural_decision" in event_types

    # Verify touched_files populated
    checkout_fix = next(m for m in timeline["milestones"] if m["event_type"] == "bug_fix")
    assert "src/checkout/service.ts" in checkout_fix["touched_files"]
    assert checkout_fix["is_defect_fix"] is True

    # Verify stats
    stats = timeline["stats"]
    assert stats is not None
    assert stats["total_milestones"] == len(timeline["milestones"])
    assert stats["total_commits"] == 4
    assert stats["defect_fixes_count"] >= 1
    assert stats["adrs_count"] >= 1
    assert stats["active_authors_count"] >= 3
    assert stats["total_insertions"] == 20 + 50 + 120 + 15 + 10
    assert stats["total_deletions"] == 5 + 30
    assert stats["net_churn"] == stats["total_insertions"] - stats["total_deletions"]
    assert len(stats["velocity"]) >= 2  # spans Jan, Feb, Mar 2025


@pytest.mark.asyncio
async def test_timeline_rest_endpoints(client: AsyncClient, db_session: AsyncSession) -> None:
    # 1. Create Repository
    repo = Repository(
        id=uuid.uuid4(),
        owner="timeline-api",
        name="api-repo",
        full_name="timeline-api/api-repo",
        default_branch="main",
    )
    db_session.add(repo)
    await db_session.commit()

    # 2. Add commits
    indexer = GitHistoryIndexer()
    commits = [
        ParsedCommit(
            commit_hash="e500000000000000000000000000000000000005",
            author_name="Dev One",
            author_email="dev1@example.com",
            committed_at=datetime(2025, 1, 10, 10, 0, 0, tzinfo=timezone.utc),
            message="feat: initial service framework",
            file_changes=[
                ParsedFileChange(
                    file_path="src/service.py",
                    change_type=ChangeType.ADDED,
                    insertions=40,
                    deletions=0,
                ),
            ],
        )
    ]
    await indexer.index_commits(repo.id, commits, db_session)

    # 3. Test GET /api/v1/repositories/{id}/timeline
    resp = await client.get(f"/api/v1/repositories/{repo.id}/timeline")
    assert resp.status_code == 200
    data = resp.json()
    assert data["repository_id"] == str(repo.id)
    assert data["component_path"] == "all"
    assert data["total_events"] >= 1
    assert data["stats"] is not None
    assert data["stats"]["total_commits"] == 1
    assert len(data["milestones"]) >= 1
    assert data["milestones"][0]["touched_files"] == ["src/service.py"]

    # 4. Test GET /api/v1/repositories/{id}/components/src/service.py/timeline
    comp_resp = await client.get(
        f"/api/v1/repositories/{repo.id}/components/src/service.py/timeline"
    )
    assert comp_resp.status_code == 200
    comp_data = comp_resp.json()
    assert comp_data["component_path"] == "src/service.py"
    assert comp_data["total_events"] >= 1
    assert comp_data["stats"] is not None
