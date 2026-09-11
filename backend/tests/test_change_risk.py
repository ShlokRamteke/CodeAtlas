from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.history.change_risk import (
    FileChangeStat,
    HistoricalCommitInfo,
    assess_change_risk,
    compute_defect_pressure,
    compute_kamei_metrics,
    compute_shannon_entropy,
    is_fix_commit,
    mine_defect_pressure_from_db,
    parse_unified_diff,
)
from app.models.commit import Commit
from app.models.commit_file_change import ChangeType, CommitFileChange
from app.models.repository import Repository


def test_shannon_entropy_calculation() -> None:
    # Single file has zero entropy (complete concentration)
    assert compute_shannon_entropy([100]) == 0.0
    assert compute_shannon_entropy([]) == 0.0

    # Two files with equal churn have entropy = 1.0 (log2(2) = 1)
    assert compute_shannon_entropy([50, 50]) == 1.0

    # Four files with equal churn have entropy = 2.0 (log2(4) = 2)
    assert compute_shannon_entropy([25, 25, 25, 25]) == 2.0

    # Skewed churn has entropy between 0 and 1
    skewed = compute_shannon_entropy([90, 10])
    assert 0.0 < skewed < 1.0


def test_kamei_metrics_computation() -> None:
    changes = [
        FileChangeStat(path="backend/app/auth/service.py", lines_added=80, lines_deleted=20),
        FileChangeStat(path="backend/app/auth/models.py", lines_added=30, lines_deleted=10),
        FileChangeStat(path="frontend/src/components/Login.tsx", lines_added=40, lines_deleted=5),
    ]

    metrics = compute_kamei_metrics(changes)

    assert metrics.lines_added == 150
    assert metrics.lines_deleted == 35
    assert metrics.files_touched == 3
    # 2 directories: backend/app/auth, frontend/src/components
    assert metrics.distinct_directories == 2
    # 2 top-level subsystems: backend, frontend
    assert metrics.distinct_subsystems == 2
    assert metrics.shannon_entropy > 1.0


def test_is_fix_commit_heuristics() -> None:
    assert is_fix_commit("fix: resolve payment null pointer error") is True
    assert is_fix_commit("Hotfix for checkout deadlock") is True
    assert is_fix_commit("Bug: user session timeout too early") is True
    assert is_fix_commit("Fixes issue with token refresh") is True
    assert is_fix_commit("Revert broken migration script") is True
    assert is_fix_commit("feat: add dark mode support") is False
    assert is_fix_commit("docs: update README.md") is False


def test_defect_pressure_exponential_decay() -> None:
    now = datetime(2026, 9, 1, tzinfo=timezone.utc)
    target = {"backend/app/payment/service.py"}

    commits = [
        # Immediate fix (0 days old) -> weight ~ 1.0
        HistoricalCommitInfo(
            hash="c1",
            message="fix: handle stripe webhook edge cases",
            timestamp=now,
            touched_files=("backend/app/payment/service.py",),
            is_fix=True,
        ),
        # Exactly 365 days old (1 half-life) -> weight ~ 0.5
        HistoricalCommitInfo(
            hash="c2",
            message="bugfix: payment retry backoff",
            timestamp=now - timedelta(days=365),
            touched_files=("backend/app/payment/service.py",),
            is_fix=True,
        ),
        # Unrelated file fix -> weight = 0
        HistoricalCommitInfo(
            hash="c3",
            message="fix: nav bar css alignment",
            timestamp=now,
            touched_files=("frontend/nav.tsx",),
            is_fix=True,
        ),
        # Non-fix commit -> weight = 0
        HistoricalCommitInfo(
            hash="c4",
            message="feat: initial payment service",
            timestamp=now,
            touched_files=("backend/app/payment/service.py",),
            is_fix=False,
        ),
    ]

    pressure = compute_defect_pressure(commits, target, reference_time=now, half_life_days=365.0)
    # Expected: 1.0 + 0.5 = 1.5
    assert abs(pressure - 1.5) < 0.05


def test_assess_change_risk_consolidated() -> None:
    now = datetime(2026, 9, 1, tzinfo=timezone.utc)

    # Large, highly-diffused change touching historical defect files
    changes = [
        FileChangeStat(path="backend/services/billing.py", lines_added=300, lines_deleted=100),
        FileChangeStat(path="frontend/pages/checkout.tsx", lines_added=150, lines_deleted=50),
        FileChangeStat(path="infra/terraform/main.tf", lines_added=50, lines_deleted=20),
    ]

    commits = [
        HistoricalCommitInfo(
            hash="h1",
            message="hotfix: billing calculation race condition",
            timestamp=now - timedelta(days=10),
            touched_files=("backend/services/billing.py",),
            is_fix=True,
        ),
        HistoricalCommitInfo(
            hash="h2",
            message="fix: checkout currency formatting bug",
            timestamp=now - timedelta(days=20),
            touched_files=("frontend/pages/checkout.tsx",),
            is_fix=True,
        ),
        HistoricalCommitInfo(
            hash="h3",
            message="fix: billing invoice rounding error",
            timestamp=now - timedelta(days=30),
            touched_files=("backend/services/billing.py",),
            is_fix=True,
        ),
    ]

    report = assess_change_risk(changes, commits, reference_time=now)

    assert report.risk_score >= 0.70
    assert report.risk_level in ("HIGH", "CRITICAL")
    assert report.kamei_metrics.files_touched == 3
    assert report.kamei_metrics.distinct_subsystems == 3
    assert report.defect_pressure >= 2.5
    assert any("Large code churn" in f for f in report.explanatory_factors)
    assert any("distinct subsystems" in f for f in report.explanatory_factors)
    assert report.fix_commit_count == 3


def test_parse_unified_diff() -> None:
    # Empty diff
    assert parse_unified_diff("") == []
    assert parse_unified_diff("   \n  ") == []

    # Standard git diff
    raw_diff = """diff --git a/backend/app/auth.py b/backend/app/auth.py
index 1234567..89abcdef 100644
--- a/backend/app/auth.py
+++ b/backend/app/auth.py
@@ -10,4 +10,6 @@
-old_auth_check()
+new_auth_check()
+validate_token()
+audit_log()
diff --git a/frontend/src/Login.tsx b/frontend/src/Login.tsx
--- a/frontend/src/Login.tsx
+++ b/frontend/src/Login.tsx
@@ -1,2 +1,3 @@
-import { old } from 'old';
+import { auth } from 'auth';
+const x = 1;
"""
    stats = parse_unified_diff(raw_diff)
    assert len(stats) == 2

    by_path = {s.path: s for s in stats}
    assert "backend/app/auth.py" in by_path
    assert by_path["backend/app/auth.py"].lines_added == 3
    assert by_path["backend/app/auth.py"].lines_deleted == 1
    assert by_path["backend/app/auth.py"].total_churn == 4

    assert "frontend/src/Login.tsx" in by_path
    assert by_path["frontend/src/Login.tsx"].lines_added == 2
    assert by_path["frontend/src/Login.tsx"].lines_deleted == 1


@pytest.mark.asyncio
async def test_mine_defect_pressure_from_db(db_session: AsyncSession) -> None:
    repo = Repository(
        owner="test-owner",
        name="risk-repo",
        full_name="test-owner/risk-repo",
        default_branch="main",
    )
    db_session.add(repo)
    await db_session.commit()
    await db_session.refresh(repo)

    now = datetime.now(timezone.utc)

    # Insert historical commits: 1 fix commit touching target, 1 non-fix commit, 1 fix commit touching unrelated
    c1 = Commit(
        repository_id=repo.id,
        commit_hash="1111111111111111111111111111111111111111",
        author_name="Dev",
        author_email="dev@example.com",
        committed_at=now - timedelta(days=10),
        message="fix: resolve critical race condition in orders",
    )
    c2 = Commit(
        repository_id=repo.id,
        commit_hash="2222222222222222222222222222222222222222",
        author_name="Dev",
        author_email="dev@example.com",
        committed_at=now - timedelta(days=20),
        message="feat: add telemetry logging in orders",
    )
    c3 = Commit(
        repository_id=repo.id,
        commit_hash="3333333333333333333333333333333333333333",
        author_name="Dev",
        author_email="dev@example.com",
        committed_at=now - timedelta(days=5),
        message="fix: update docs css styling",
    )
    db_session.add_all([c1, c2, c3])
    await db_session.commit()
    await db_session.refresh(c1)
    await db_session.refresh(c2)
    await db_session.refresh(c3)

    fc1 = CommitFileChange(
        commit_id=c1.id,
        file_path="backend/app/orders.py",
        change_type=ChangeType.MODIFIED,
        insertions=10,
        deletions=2,
    )
    fc2 = CommitFileChange(
        commit_id=c2.id,
        file_path="backend/app/orders.py",
        change_type=ChangeType.MODIFIED,
        insertions=5,
        deletions=0,
    )
    fc3 = CommitFileChange(
        commit_id=c3.id,
        file_path="docs/style.css",
        change_type=ChangeType.MODIFIED,
        insertions=1,
        deletions=1,
    )
    db_session.add_all([fc1, fc2, fc3])
    await db_session.commit()

    # Mine defect pressure for target file backend/app/orders.py
    pressure, fix_commits = await mine_defect_pressure_from_db(
        db=db_session,
        repository_id=repo.id,
        target_files={"backend/app/orders.py"},
        limit=20000,
        half_life_days=365.0,
        reference_time=now,
    )

    assert pressure > 0.9  # 10 days old with 365d half-life ~ 0.98
    assert len(fix_commits) == 1
    assert fix_commits[0].hash == "1111111111111111111111111111111111111111"
    assert "backend/app/orders.py" in fix_commits[0].touched_files
