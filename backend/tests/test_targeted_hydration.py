from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.history.historical_linker import HistoricalLinker, ParsedIssue, ParsedPullRequest
from app.models.commit import Commit
from app.models.historical_link import CommitIssueLink, CommitPullRequestLink
from app.models.issue import Issue
from app.models.pull_request import PullRequest
from app.models.repository import Repository


@pytest.mark.asyncio
async def test_targeted_reference_hydration(db_session: AsyncSession) -> None:
    # 1. Setup repository
    repo = Repository(
        owner="hydra-test",
        name="reference-app",
        full_name="hydra-test/reference-app",
    )
    db_session.add(repo)
    await db_session.commit()
    await db_session.refresh(repo)

    # 2. Add commits with unlinked references (e.g. PR #88 and Issue #99, not in DB)
    from datetime import datetime, timezone

    commit = Commit(
        repository_id=repo.id,
        commit_hash="abc1234567890",
        author_name="Alice",
        author_email="alice@test.com",
        committed_at=datetime.now(timezone.utc),
        message="feat(core): implement feature\n\nFixes #99. PR #88",
    )
    db_session.add(commit)
    await db_session.commit()
    await db_session.refresh(commit)

    linker = HistoricalLinker()
    # Link commit -> creates unlinked CommitPullRequestLink (PR #88) and CommitIssueLink (Issue #99)
    await linker.link_commit(repo.id, commit, db_session)

    # Verify unlinked links exist
    pr_links = (
        (
            await db_session.execute(
                select(CommitPullRequestLink).where(CommitPullRequestLink.commit_id == commit.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(pr_links) == 1
    assert pr_links[0].pr_number == 88
    assert pr_links[0].pull_request_id is None

    issue_links = (
        (
            await db_session.execute(
                select(CommitIssueLink).where(CommitIssueLink.commit_id == commit.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(issue_links) == 1
    assert issue_links[0].issue_number == 99
    assert issue_links[0].issue_id is None

    # 3. Create mock fetcher that returns the targeted items
    mock_fetcher = AsyncMock()
    mock_fetcher.fetch_single_pull_request.return_value = ParsedPullRequest(
        number=88,
        title="feat(core): pull request 88",
        state="merged",
        author="Alice",
        html_url="https://github.com/hydra-test/reference-app/pull/88",
    )
    mock_fetcher.fetch_single_issue.return_value = ParsedIssue(
        number=99,
        title="Bug in core feature",
        state="closed",
        author="Bob",
        html_url="https://github.com/hydra-test/reference-app/issues/99",
    )

    # 4. Run targeted hydration
    hydration_res = await linker.hydrate_missing_references(
        repository_id=repo.id,
        db=db_session,
        fetcher=mock_fetcher,
    )
    assert hydration_res["hydrated_prs"] == 1
    assert hydration_res["hydrated_issues"] == 1

    # 5. Verify PR & Issue are persisted in DB
    persisted_pr = (
        await db_session.execute(
            select(PullRequest).where(
                PullRequest.repository_id == repo.id, PullRequest.number == 88
            )
        )
    ).scalar_one_or_none()
    assert persisted_pr is not None
    assert persisted_pr.title == "feat(core): pull request 88"

    persisted_issue = (
        await db_session.execute(
            select(Issue).where(Issue.repository_id == repo.id, Issue.number == 99)
        )
    ).scalar_one_or_none()
    assert persisted_issue is not None
    assert persisted_issue.title == "Bug in core feature"

    # 6. Verify links are now populated with foreign keys
    await db_session.refresh(pr_links[0])
    await db_session.refresh(issue_links[0])
    assert pr_links[0].pull_request_id == persisted_pr.id
    assert issue_links[0].issue_id == persisted_issue.id


@pytest.mark.asyncio
async def test_hydrate_api_endpoint(client: AsyncClient) -> None:
    # 1. Create repo
    create_res = await client.post(
        "/api/v1/repositories/",
        json={"owner": "api-hydrate", "name": "app", "full_name": "api-hydrate/app"},
    )
    assert create_res.status_code == 201
    repo_id = create_res.json()["id"]

    # 2. Call hydrate endpoint (with no missing refs)
    res = await client.post(f"/api/v1/repositories/{repo_id}/references/hydrate")
    assert res.status_code == 200
    data = res.json()
    assert data["hydrated_prs"] == 0
    assert data["hydrated_issues"] == 0
    assert "Targeted hydration complete" in data["message"]
