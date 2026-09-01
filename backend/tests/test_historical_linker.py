from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.history.git_indexer import GitHistoryIndexer, ParsedCommit, ParsedFileChange
from app.history.historical_linker import (
    HistoricalLinker,
    ParsedIssue,
    ParsedPullRequest,
)
from app.models.commit_file_change import ChangeType
from app.models.repository import Repository


@pytest.mark.asyncio
async def test_historical_linking_and_trace(db_session: AsyncSession):
    # 1. Create Repository
    repo = Repository(
        id=uuid.uuid4(),
        owner="test-org",
        name="test-trace-repo",
        full_name="test-org/test-trace-repo",
        default_branch="main",
    )
    db_session.add(repo)
    await db_session.commit()

    linker = HistoricalLinker()
    git_indexer = GitHistoryIndexer()

    # 2. Ingest PRs
    prs = [
        ParsedPullRequest(
            number=42,
            title="feat: Add user authentication system",
            body="Implements JWT auth.\n\nFixes #101\nRefs #102",
            state="merged",
            author="alice",
            merged_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
            labels=["enhancement", "security"],
            html_url="https://github.com/test-org/test-trace-repo/pull/42",
        ),
        ParsedPullRequest(
            number=43,
            title="fix: Patch token expiration bug",
            body="Resolves #103",
            state="merged",
            author="bob",
            merged_at=datetime(2026, 3, 5, 12, 0, 0, tzinfo=timezone.utc),
            labels=["bug"],
            html_url="https://github.com/test-org/test-trace-repo/pull/43",
        ),
    ]
    pr_count = await linker.index_pull_requests(repo.id, prs, db_session)
    assert pr_count == 2

    # 3. Ingest Issues
    issues = [
        ParsedIssue(
            number=101,
            title="Require JWT authentication for API",
            body="All v1 endpoints must require bearer token.",
            state="closed",
            author="product-lead",
            closed_at=datetime(2026, 3, 1, 10, 0, 0, tzinfo=timezone.utc),
            labels=["security", "v1"],
            html_url="https://github.com/test-org/test-trace-repo/issues/101",
        ),
        ParsedIssue(
            number=102,
            title="Document auth architecture in README",
            body="Add sequence diagrams for login.",
            state="open",
            author="tech-writer",
            labels=["docs"],
            html_url="https://github.com/test-org/test-trace-repo/issues/102",
        ),
        ParsedIssue(
            number=103,
            title="Token refresh expires prematurely on iOS",
            body="Investigate clock drift on iOS clients.",
            state="closed",
            author="qa-tester",
            closed_at=datetime(2026, 3, 5, 12, 0, 0, tzinfo=timezone.utc),
            labels=["bug", "mobile"],
            html_url="https://github.com/test-org/test-trace-repo/issues/103",
        ),
    ]
    issue_count = await linker.index_issues(repo.id, issues, db_session)
    assert issue_count == 3

    # 4. Ingest Commits with reference patterns
    commits = [
        ParsedCommit(
            commit_hash="c111111111111111111111111111111111111111",
            author_name="Alice",
            author_email="alice@example.com",
            committed_at=datetime(2026, 3, 1, 9, 30, 0, tzinfo=timezone.utc),
            message="feat(auth): initial JWT token generator (PR #42) - fixes #101",
            file_changes=[
                ParsedFileChange(
                    file_path="src/auth/jwt.py",
                    change_type=ChangeType.ADDED,
                    insertions=120,
                    deletions=0,
                )
            ],
        ),
        ParsedCommit(
            commit_hash="c222222222222222222222222222222222222222",
            author_name="Bob",
            author_email="bob@example.com",
            committed_at=datetime(2026, 3, 5, 11, 45, 0, tzinfo=timezone.utc),
            message="Merge pull request #43 from bugfix/token-drift\n\nFixes #103",
            file_changes=[
                ParsedFileChange(
                    file_path="src/auth/jwt.py",
                    change_type=ChangeType.MODIFIED,
                    insertions=15,
                    deletions=3,
                )
            ],
        ),
    ]
    commit_count = await git_indexer.index_commits(repo.id, commits, db_session)
    assert commit_count == 2

    # 5. Query Full Historical Trace for src/auth/jwt.py
    trace = await linker.get_historical_trace(repo.id, "src/auth/jwt.py", db_session)

    assert trace["file_path"] == "src/auth/jwt.py"
    assert trace["total_commits"] == 2
    assert trace["total_pull_requests"] == 2
    assert trace["total_issues"] >= 2

    # Check commit level links
    first_commit = trace["trace_chain"][0]  # Latest commit (c2222...)
    assert first_commit["commit_hash"] == "c222222222222222222222222222222222222222"
    assert len(first_commit["linked_pull_requests"]) == 1
    assert first_commit["linked_pull_requests"][0]["number"] == 43
    assert len(first_commit["linked_issues"]) == 1
    assert first_commit["linked_issues"][0]["number"] == 103

    second_commit = trace["trace_chain"][1]  # Origin commit (c1111...)
    assert second_commit["commit_hash"] == "c111111111111111111111111111111111111111"
    assert second_commit["change_type"] == "added"
    assert len(second_commit["linked_pull_requests"]) == 1
    assert second_commit["linked_pull_requests"][0]["number"] == 42
    # PR #42 links to Issue #101 and #102
    assert len(second_commit["linked_pull_requests"][0]["linked_issues"]) == 2
