from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.investigation.concurrent_overlap import (
    ConcurrentOverlapDetector,
)
from app.investigation.distillation import TokenBudgetDistiller
from app.models.commit import Commit
from app.models.commit_file_change import ChangeType, CommitFileChange
from app.models.historical_link import CommitPullRequestLink
from app.models.investigation import Investigation, InvestigationStatus, InvestigationType
from app.models.pull_request import PullRequest, PullRequestState
from app.models.repository import Repository


@pytest.mark.asyncio
async def test_detect_overlaps_direct_collision(db_session: AsyncSession) -> None:
    repo_id = uuid.uuid4()
    repo = Repository(id=repo_id, owner="owner", name="repo-direct", full_name="owner/repo-direct")
    db_session.add(repo)
    await db_session.commit()

    pr1 = PullRequest(
        id=uuid.uuid4(),
        repository_id=repo_id,
        number=101,
        title="Refactor auth session logic",
        state=PullRequestState.OPEN,
        author="alice",
        head_branch="feat/auth-session",
        base_branch="main",
        touched_files=["app/auth/session.py", "app/auth/tokens.py"],
    )
    db_session.add(pr1)
    await db_session.commit()

    detector = ConcurrentOverlapDetector()
    report = await detector.detect_overlaps(
        db=db_session,
        repository_id=repo_id,
        target_files=["app/auth/session.py", "app/main.py"],
    )

    assert report.total_open_prs == 1
    assert report.overlapping_pr_count == 1
    assert report.has_direct_conflicts is True
    assert report.highest_risk_level == "HIGH"
    assert report.overlapping_prs[0].pr_number == 101
    assert report.overlapping_prs[0].overlap_type == "direct_target"
    assert report.overlapping_prs[0].direct_overlapping_files == ["app/auth/session.py"]
    assert "Direct file conflict with PR #101" in report.overlapping_prs[0].recommendation


@pytest.mark.asyncio
async def test_detect_overlaps_multiple_direct_files_is_critical(db_session: AsyncSession) -> None:
    repo_id = uuid.uuid4()
    repo = Repository(
        id=repo_id,
        owner="owner",
        name="repo-multi-collision",
        full_name="owner/repo-multi-collision",
    )
    db_session.add(repo)
    await db_session.commit()

    pr = PullRequest(
        id=uuid.uuid4(),
        repository_id=repo_id,
        number=202,
        title="Revamp database models",
        state=PullRequestState.OPEN,
        author="bob",
        head_branch="feat/db-models",
        base_branch="main",
        touched_files=["app/models/user.py", "app/models/account.py"],
    )
    db_session.add(pr)
    await db_session.commit()

    detector = ConcurrentOverlapDetector()
    report = await detector.detect_overlaps(
        db=db_session,
        repository_id=repo_id,
        target_files=["app/models/user.py", "app/models/account.py"],
    )

    assert report.overlapping_pr_count == 1
    assert report.has_direct_conflicts is True
    assert report.highest_risk_level == "CRITICAL"
    assert len(report.overlapping_prs[0].direct_overlapping_files) == 2


@pytest.mark.asyncio
async def test_detect_overlaps_blast_radius_dependency(db_session: AsyncSession) -> None:
    repo_id = uuid.uuid4()
    repo = Repository(
        id=repo_id,
        owner="owner",
        name="repo-blast",
        full_name="owner/repo-blast",
    )
    db_session.add(repo)
    await db_session.commit()

    pr = PullRequest(
        id=uuid.uuid4(),
        repository_id=repo_id,
        number=303,
        title="Update HTTP client configurations",
        state=PullRequestState.OPEN,
        author="carol",
        head_branch="chore/http-client",
        base_branch="main",
        touched_files=["app/core/client.py"],
    )
    db_session.add(pr)
    await db_session.commit()

    detector = ConcurrentOverlapDetector()
    report = await detector.detect_overlaps(
        db=db_session,
        repository_id=repo_id,
        target_files=["app/services/fetcher.py"],
        blast_radius_files=["app/core/client.py", "app/utils/logger.py"],
    )

    assert report.has_direct_conflicts is False
    assert report.has_blast_conflicts is True
    assert report.highest_risk_level == "MEDIUM"
    assert report.overlapping_prs[0].overlap_type == "blast_radius"
    assert report.overlapping_prs[0].blast_overlapping_files == ["app/core/client.py"]


@pytest.mark.asyncio
async def test_detect_overlaps_ignores_closed_or_merged(db_session: AsyncSession) -> None:
    repo_id = uuid.uuid4()
    repo = Repository(
        id=repo_id,
        owner="owner",
        name="repo-closed",
        full_name="owner/repo-closed",
    )
    db_session.add(repo)
    await db_session.commit()

    pr_closed = PullRequest(
        id=uuid.uuid4(),
        repository_id=repo_id,
        number=401,
        title="Closed PR",
        state=PullRequestState.CLOSED,
        author="dave",
        touched_files=["app/models/user.py"],
    )
    pr_merged = PullRequest(
        id=uuid.uuid4(),
        repository_id=repo_id,
        number=402,
        title="Merged PR",
        state=PullRequestState.MERGED,
        author="eve",
        touched_files=["app/models/user.py"],
    )
    db_session.add_all([pr_closed, pr_merged])
    await db_session.commit()

    detector = ConcurrentOverlapDetector()
    report = await detector.detect_overlaps(
        db=db_session,
        repository_id=repo_id,
        target_files=["app/models/user.py"],
    )

    assert report.total_open_prs == 0
    assert report.overlapping_pr_count == 0
    assert report.has_direct_conflicts is False
    assert report.highest_risk_level == "NONE"


@pytest.mark.asyncio
async def test_detect_overlaps_via_linked_commits(db_session: AsyncSession) -> None:
    repo_id = uuid.uuid4()
    repo = Repository(
        id=repo_id,
        owner="owner",
        name="repo-commits",
        full_name="owner/repo-commits",
    )
    db_session.add(repo)
    await db_session.commit()

    # Create Commit and FileChange
    commit_id = uuid.uuid4()
    commit = Commit(
        id=commit_id,
        repository_id=repo_id,
        commit_hash="abc1234567890",
        message="Update payment handler",
        author_name="frank",
        author_email="frank@test.com",
        committed_at=datetime.now(timezone.utc),
    )
    fc = CommitFileChange(
        id=uuid.uuid4(),
        commit_id=commit_id,
        file_path="app/payments/stripe.py",
        change_type=ChangeType.MODIFIED,
    )
    commit.file_changes = [fc]
    db_session.add(commit)

    # Open PR with no touched_files, but linked to commit
    pr = PullRequest(
        id=uuid.uuid4(),
        repository_id=repo_id,
        number=505,
        title="Stripe payment webhook updates",
        state=PullRequestState.OPEN,
        author="frank",
        head_branch="feat/stripe-webhook",
        touched_files=[],  # empty
    )
    db_session.add(pr)
    await db_session.flush()

    link = CommitPullRequestLink(
        id=uuid.uuid4(),
        commit_id=commit.id,
        pull_request_id=pr.id,
        pr_number=505,
    )
    db_session.add(link)
    await db_session.commit()

    detector = ConcurrentOverlapDetector()
    report = await detector.detect_overlaps(
        db=db_session,
        repository_id=repo_id,
        target_files=["app/payments/stripe.py"],
    )

    assert report.overlapping_pr_count == 1
    assert report.has_direct_conflicts is True
    assert report.overlapping_prs[0].pr_number == 505
    assert report.overlapping_prs[0].direct_overlapping_files == ["app/payments/stripe.py"]


@pytest.mark.asyncio
async def test_concurrent_overlap_api_endpoints(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    repo_id = uuid.uuid4()
    repo = Repository(
        id=repo_id,
        owner="owner",
        name="repo-api-overlap",
        full_name="owner/repo-api-overlap",
    )
    db_session.add(repo)
    await db_session.commit()

    pr = PullRequest(
        id=uuid.uuid4(),
        repository_id=repo_id,
        number=601,
        title="API rate limiting middleware",
        state=PullRequestState.OPEN,
        author="grace",
        head_branch="feat/rate-limit",
        touched_files=["app/api/middleware.py"],
    )
    db_session.add(pr)
    await db_session.commit()

    # 1. Test repository endpoint: GET /api/v1/repositories/{id}/concurrent-overlap
    res1 = await client.get(
        f"/api/v1/repositories/{repo_id}/concurrent-overlap?target_files=app/api/middleware.py"
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["has_direct_conflicts"] is True
    assert data1["overlapping_pr_count"] == 1
    assert data1["overlapping_prs"][0]["pr_number"] == 601

    # 2. Test investigation endpoint: GET /api/v1/investigations/{id}/concurrent-overlap
    inv = Investigation(
        id=uuid.uuid4(),
        repository_id=repo_id,
        query="Refactor middleware",
        type=InvestigationType.BEFORE_CHANGE,
        status=InvestigationStatus.COMPLETED,
    )
    db_session.add(inv)
    await db_session.commit()

    res2 = await client.get(f"/api/v1/investigations/{inv.id}/concurrent-overlap")
    assert res2.status_code == 200
    data2 = res2.json()
    assert "total_open_prs" in data2


def test_distillation_projection_with_concurrent_overlap() -> None:
    brief = {
        "intent_summary": "Update auth tokens in session.py",
        "target_files": ["app/auth/session.py"],
        "target_symbols": ["SessionManager"],
        "signals": {
            "concurrent_overlaps": {
                "total_open_prs": 2,
                "overlapping_pr_count": 1,
                "has_direct_conflicts": True,
                "highest_risk_level": "HIGH",
                "summary": "DETECTED 1 open PR with direct target file collisions.",
                "overlapping_prs": [
                    {
                        "pr_number": 77,
                        "pr_title": "Fix token expiration bug",
                        "pr_author": "heidi",
                        "head_branch": "fix/token-exp",
                        "risk_level": "HIGH",
                        "overlap_type": "direct_target",
                        "overlapping_files": ["app/auth/session.py"],
                        "recommendation": "Coordinate with @heidi on PR #77.",
                    }
                ],
            }
        },
    }

    # Markdown projection
    md_result = TokenBudgetDistiller.distill_brief(brief, output_format="markdown")
    assert "Concurrent In-Flight Changes" in md_result.content_text
    assert "PR #77" in md_result.content_text
    assert "MERGE CONFLICT RISK" in md_result.content_text

    # Dense Agent JSON projection
    json_result = TokenBudgetDistiller.distill_brief(brief, output_format="json")
    import json

    data = json.loads(json_result.content_text)
    assert "concurrent_overlaps" in data
    assert data["concurrent_overlaps"]["has_direct_conflicts"] is True
    assert data["concurrent_overlaps"]["highest_risk"] == "HIGH"
