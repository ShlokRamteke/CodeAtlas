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
async def test_component_timeline_generation(db_session: AsyncSession) -> None:
    # 1. Create Repository
    repo = Repository(
        id=uuid.uuid4(),
        owner="timeline-test",
        name="timeline-repo",
        full_name="timeline-test/timeline-repo",
        default_branch="main",
    )
    db_session.add(repo)
    await db_session.commit()

    # 2. Add an ADR mentioning the auth component
    eng_indexer = EngineeringContextIndexer(db_session)
    await eng_indexer.index_document(
        repository_id=repo.id,
        path="docs/adr/0001-jwt-auth.md",
        raw_content="""# ADR 0001: Use JWT for auth service

## Status
Accepted

## Context
We need a stateless auth service for our auth component.

## Decision
The system MUST use RS256 JWT tokens for auth requests.
""",
    )
    await db_session.commit()

    # 3. Add PRs and Issues
    linker = HistoricalLinker()
    prs = [
        ParsedPullRequest(
            number=12,
            title="feat(auth): OAuth2 refresh token rotation",
            body="Implements rotation.",
            state="merged",
            author="bob",
            merged_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            labels=["auth"],
            html_url="https://github.com/timeline-test/timeline-repo/pull/12",
        )
    ]
    await linker.index_pull_requests(repo.id, prs, db_session)

    issues = [
        ParsedIssue(
            number=42,
            title="Clock skew token expiration bug",
            body="Token expires prematurely.",
            state="closed",
            author="tester",
            closed_at=datetime(2025, 2, 1, 9, 0, 0, tzinfo=timezone.utc),
            labels=["bug"],
            html_url="https://github.com/timeline-test/timeline-repo/issues/42",
        )
    ]
    await linker.index_issues(repo.id, issues, db_session)

    # 4. Add commits spanning milestones
    indexer = GitHistoryIndexer()
    commits = [
        ParsedCommit(
            commit_hash="c_intro_001",
            author_name="Alice",
            author_email="alice@test.com",
            committed_at=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            message="feat: initial auth service bootstrap",
            file_changes=[
                ParsedFileChange(
                    file_path="src/auth/service.py",
                    change_type=ChangeType.ADDED,
                    insertions=120,
                    deletions=0,
                )
            ],
        ),
        ParsedCommit(
            commit_hash="c_feat_002",
            author_name="Bob",
            author_email="bob@test.com",
            committed_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
            message="feat(auth): implement oauth2 refresh token rotation (PR #12)",
            file_changes=[
                ParsedFileChange(
                    file_path="src/auth/service.py",
                    change_type=ChangeType.MODIFIED,
                    insertions=65,
                    deletions=5,
                )
            ],
        ),
        ParsedCommit(
            commit_hash="c_fix_003",
            author_name="Alice",
            author_email="alice@test.com",
            committed_at=datetime(2025, 2, 1, 9, 0, 0, tzinfo=timezone.utc),
            message="fix(auth): resolve token expiration clock skew bug. Closes #42",
            file_changes=[
                ParsedFileChange(
                    file_path="src/auth/service.py",
                    change_type=ChangeType.MODIFIED,
                    insertions=10,
                    deletions=2,
                )
            ],
        ),
        ParsedCommit(
            commit_hash="c_refactor_004",
            author_name="Charlie",
            author_email="charlie@test.com",
            committed_at=datetime(2025, 2, 20, 16, 0, 0, tzinfo=timezone.utc),
            message="refactor(auth): cleanup token validation pipeline and modularize handler",
            file_changes=[
                ParsedFileChange(
                    file_path="src/auth/service.py",
                    change_type=ChangeType.MODIFIED,
                    insertions=20,
                    deletions=25,
                )
            ],
        ),
    ]

    await indexer.index_commits(repo.id, commits, db_session)
    await linker.hydrate_missing_references(repo.id, db_session)

    # 4. Generate component timeline
    timeline = await indexer.get_component_timeline(repo.id, "src/auth", db_session)

    assert timeline["component_path"] == "src/auth"
    assert timeline["total_events"] >= 4
    assert timeline["introducing_event"] is not None
    assert timeline["introducing_event"]["event_type"] == "introduction"

    milestones = timeline["milestones"]
    types = [m["event_type"] for m in milestones]

    # Verify milestone types were classified properly
    assert "introduction" in types
    assert "feature_addition" in types
    assert "bug_fix" in types
    assert "refactor" in types
    assert "architectural_decision" in types

    # Verify ADR was linked
    adr_event = next(m for m in milestones if m["event_type"] == "architectural_decision")
    assert len(adr_event["linked_adrs"]) == 1
    assert "jwt" in adr_event["title"].lower() or "auth" in adr_event["title"].lower()
    assert any("doc:adr" in c for c in adr_event["citations"])

    # Verify bug fix has issue link and citation
    fix_event = next(m for m in milestones if m["event_type"] == "bug_fix")
    assert any("github:issue:42" in c for c in fix_event["citations"])


@pytest.mark.asyncio
async def test_component_timeline_api(client: AsyncClient) -> None:
    # 1. Create repo
    res = await client.post(
        "/api/v1/repositories/",
        json={"owner": "timeline-api", "name": "app", "full_name": "timeline-api/app"},
    )
    assert res.status_code == 201
    repo_id = res.json()["id"]

    # 2. Ingest commits
    commits_payload = [
        {
            "commit_hash": "c100",
            "author_name": "Developer",
            "author_email": "dev@example.com",
            "committed_at": "2025-01-01T00:00:00Z",
            "message": "feat: initial commit for user module",
            "insertions": 100,
            "deletions": 0,
            "file_changes": [
                {
                    "file_path": "src/users/controller.py",
                    "change_type": "added",
                    "insertions": 100,
                    "deletions": 0,
                }
            ],
        },
        {
            "commit_hash": "c101",
            "author_name": "Developer",
            "author_email": "dev@example.com",
            "committed_at": "2025-01-10T00:00:00Z",
            "message": "fix: bug in user password validation",
            "insertions": 5,
            "deletions": 1,
            "file_changes": [
                {
                    "file_path": "src/users/controller.py",
                    "change_type": "modified",
                    "insertions": 5,
                    "deletions": 1,
                }
            ],
        },
    ]
    c_res = await client.post(
        f"/api/v1/repositories/{repo_id}/commits/ingest",
        json={"commits": commits_payload},
    )
    assert c_res.status_code == 200

    # 3. Fetch component timeline
    t_res = await client.get(f"/api/v1/repositories/{repo_id}/components/src/users/timeline")
    assert t_res.status_code == 200
    data = t_res.json()

    assert data["component_path"] == "src/users"
    assert data["total_events"] == 2
    assert data["introducing_event"]["commit_hash"] == "c100"
    assert data["introducing_event"]["event_type"] == "introduction"
    assert data["milestones"][1]["event_type"] == "bug_fix"
    assert "user" in data["summary"].lower()


@pytest.mark.asyncio
async def test_root_component_timeline_and_no_fake_adrs(db_session: AsyncSession) -> None:
    """Verify that root component matches root files and general docs are NOT treated as ADRs."""
    repo = Repository(
        id=uuid.uuid4(),
        owner="root-test",
        name="root-repo",
        full_name="root-test/root-repo",
        default_branch="main",
    )
    db_session.add(repo)
    await db_session.commit()

    # Index general docs (AGENTS.md, README.md) - NOT ADRs!
    eng_indexer = EngineeringContextIndexer(db_session)
    await eng_indexer.index_document(
        repository_id=repo.id,
        path="AGENTS.md",
        raw_content="# Development Rules\nKeep answers short.",
    )
    await eng_indexer.index_document(
        repository_id=repo.id,
        path="README.md",
        raw_content="# Root Repo\nThis is the project root.",
    )
    await db_session.commit()

    # Index root-level commits
    indexer = GitHistoryIndexer()
    commits = [
        ParsedCommit(
            commit_hash="root_c1",
            author_name="Alice",
            author_email="alice@test.com",
            committed_at=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            message="feat: initial project root config",
            file_changes=[
                ParsedFileChange(
                    file_path="package.json",
                    change_type=ChangeType.ADDED,
                    insertions=30,
                    deletions=0,
                ),
                ParsedFileChange(
                    file_path="AGENTS.md",
                    change_type=ChangeType.ADDED,
                    insertions=10,
                    deletions=0,
                ),
            ],
        ),
        ParsedCommit(
            commit_hash="root_c2",
            author_name="Bob",
            author_email="bob@test.com",
            committed_at=datetime(2025, 1, 5, 12, 0, 0, tzinfo=timezone.utc),
            message="chore: update root dependencies in package.json",
            file_changes=[
                ParsedFileChange(
                    file_path="package.json",
                    change_type=ChangeType.MODIFIED,
                    insertions=5,
                    deletions=2,
                )
            ],
        ),
    ]
    await indexer.index_commits(repo.id, commits, db_session)

    # Fetch timeline for "root"
    timeline = await indexer.get_component_timeline(repo.id, "root", db_session)

    # 1. Commits to root files must be found
    assert timeline["component_path"] == "root"
    assert timeline["total_events"] == 2
    assert timeline["introducing_event"] is not None
    assert timeline["introducing_event"]["commit_hash"] == "root_c1"
    assert len(timeline["top_authors"]) == 2

    # 2. General docs MUST NOT be counted as ADRs
    adr_milestones = [
        m for m in timeline["milestones"] if m["event_type"] == "architectural_decision"
    ]
    assert len(adr_milestones) == 0  # 0 fake ADRs!
