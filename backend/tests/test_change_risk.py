from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest

from app.history.change_risk import (
    FileChangeStat,
    HistoricalCommitInfo,
    assess_change_risk,
    compute_defect_pressure,
    compute_kamei_metrics,
    compute_shannon_entropy,
    is_fix_commit,
)


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
