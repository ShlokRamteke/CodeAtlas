from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.investigation.ownership import (
    CodeOwnershipAnalyzer,
    CommitChangeItem,
)


def test_empty_ownership():
    report = CodeOwnershipAnalyzer.analyze_ownership(
        target_files=[],
        blast_radius_files=[],
        commit_records=[],
    )
    assert report.target_files == []
    assert report.blast_radius_files == []
    assert report.file_ownerships == []
    assert report.recommended_reviewers == []
    assert report.overall_bus_factor == 1


def test_single_author_high_ownership_and_bus_factor_1():
    now = datetime.now(timezone.utc)
    records = [
        CommitChangeItem(
            commit_hash="c1",
            author_name="Alice Dev",
            author_email="alice@example.com",
            committed_at=now - timedelta(days=5),
            file_path="backend/app/main.py",
            insertions=100,
            deletions=10,
        ),
        CommitChangeItem(
            commit_hash="c2",
            author_name="Alice Dev",
            author_email="alice@example.com",
            committed_at=now - timedelta(days=2),
            file_path="backend/app/main.py",
            insertions=50,
            deletions=5,
        ),
    ]

    report = CodeOwnershipAnalyzer.analyze_ownership(
        target_files=["backend/app/main.py"],
        commit_records=records,
        reference_time=now,
    )

    assert len(report.file_ownerships) == 1
    fo = report.file_ownerships[0]
    assert fo.file_path == "backend/app/main.py"
    assert fo.total_commits == 2
    assert fo.primary_owner is not None
    assert fo.primary_owner.author_name == "Alice Dev"
    assert fo.primary_owner.ownership_percentage == 100.0
    assert fo.ownership_level == "HIGH"
    assert fo.bus_factor == 1
    assert report.overall_bus_factor == 1
    # Check bus factor = 1 warning
    assert any("Bus Factor = 1" in w for w in report.knowledge_loss_warnings)
    # Reviewer recommended
    assert len(report.recommended_reviewers) == 1
    assert report.recommended_reviewers[0].author_name == "Alice Dev"
    assert report.recommended_reviewers[0].role == "PRIMARY_OWNER"


def test_recency_decay_favors_recent_maintainer():
    now = datetime.now(timezone.utc)
    # Alice touched 2000 lines 400 days ago (more than 2 half-lives: 180 * 2 = 360)
    # Bob touched 700 lines 5 days ago (almost 0 decay)
    records = [
        CommitChangeItem(
            commit_hash="c1",
            author_name="Alice Inactive",
            author_email="alice@example.com",
            committed_at=now - timedelta(days=400),
            file_path="backend/app/service.py",
            insertions=1800,
            deletions=200,
        ),
        CommitChangeItem(
            commit_hash="c2",
            author_name="Bob Active",
            author_email="bob@example.com",
            committed_at=now - timedelta(days=5),
            file_path="backend/app/service.py",
            insertions=600,
            deletions=100,
        ),
    ]

    report = CodeOwnershipAnalyzer.analyze_ownership(
        target_files=["backend/app/service.py"],
        commit_records=records,
        reference_time=now,
        half_life_days=180.0,
    )

    fo = report.file_ownerships[0]
    assert fo.primary_owner is not None
    # Bob should be primary owner despite lower raw churn due to exponential recency decay
    assert fo.primary_owner.author_name == "Bob Active"
    assert fo.primary_owner.decayed_churn > fo.all_contributors[1].decayed_churn
    assert report.recommended_reviewers[0].author_name == "Bob Active"


def test_file_bus_factor_multiple_contributors():
    now = datetime.now(timezone.utc)
    # 3 contributors with roughly equal recent churn (33% each)
    records = [
        CommitChangeItem(
            commit_hash="c1",
            author_name="Alice",
            author_email="alice@example.com",
            committed_at=now - timedelta(days=2),
            file_path="app/router.py",
            insertions=100,
            deletions=0,
        ),
        CommitChangeItem(
            commit_hash="c2",
            author_name="Bob",
            author_email="bob@example.com",
            committed_at=now - timedelta(days=3),
            file_path="app/router.py",
            insertions=100,
            deletions=0,
        ),
        CommitChangeItem(
            commit_hash="c3",
            author_name="Charlie",
            author_email="charlie@example.com",
            committed_at=now - timedelta(days=4),
            file_path="app/router.py",
            insertions=100,
            deletions=0,
        ),
    ]

    report = CodeOwnershipAnalyzer.analyze_ownership(
        target_files=["app/router.py"],
        commit_records=records,
        reference_time=now,
    )

    fo = report.file_ownerships[0]
    assert len(fo.all_contributors) == 3
    # With ~33% each, 1 contributor (33%) < 75%, 2 contributors (66%) < 75%, 3 contributors (100%) >= 75%
    assert fo.bus_factor == 3
    assert fo.ownership_level == "DIFFUSED"
    assert report.overall_bus_factor == 3


def test_reviewer_recommendation_and_roles():
    now = datetime.now(timezone.utc)
    records = [
        # Alice maintains target file
        CommitChangeItem(
            commit_hash="c1",
            author_name="Alice Lead",
            author_email="alice@example.com",
            committed_at=now - timedelta(days=2),
            file_path="backend/app/auth.py",
            insertions=300,
            deletions=20,
        ),
        # Bob maintains downstream caller in blast radius
        CommitChangeItem(
            commit_hash="c2",
            author_name="Bob Guardian",
            author_email="bob@example.com",
            committed_at=now - timedelta(days=5),
            file_path="backend/app/users.py",
            insertions=400,
            deletions=50,
        ),
    ]

    report = CodeOwnershipAnalyzer.analyze_ownership(
        target_files=["backend/app/auth.py"],
        blast_radius_files=["backend/app/users.py"],
        commit_records=records,
        reference_time=now,
    )

    rev_map = {r.author_name: r for r in report.recommended_reviewers}
    assert "Alice Lead" in rev_map
    assert "Bob Guardian" in rev_map
    assert rev_map["Alice Lead"].role == "PRIMARY_OWNER"
    assert rev_map["Bob Guardian"].role == "BLAST_RADIUS_GUARDIAN"
    assert "backend/app/auth.py" in rev_map["Alice Lead"].target_files_owned
    assert "backend/app/users.py" in rev_map["Bob Guardian"].blast_radius_files_owned


def test_current_author_exclusion():
    now = datetime.now(timezone.utc)
    records = [
        CommitChangeItem(
            commit_hash="c1",
            author_name="Alice Lead",
            author_email="alice@example.com",
            committed_at=now - timedelta(days=2),
            file_path="backend/app/auth.py",
            insertions=300,
            deletions=20,
        ),
        CommitChangeItem(
            commit_hash="c2",
            author_name="Bob Reviewer",
            author_email="bob@example.com",
            committed_at=now - timedelta(days=5),
            file_path="backend/app/auth.py",
            insertions=100,
            deletions=10,
        ),
    ]

    # If Alice is current author making the PR, she must not be recommended to review her own change
    report = CodeOwnershipAnalyzer.analyze_ownership(
        target_files=["backend/app/auth.py"],
        commit_records=records,
        current_author="Alice Lead",
        reference_time=now,
    )

    reviewers = [r.author_name for r in report.recommended_reviewers]
    assert "Alice Lead" not in reviewers
    assert "Bob Reviewer" in reviewers


def test_knowledge_loss_warning_for_inactive_primary_author():
    now = datetime.now(timezone.utc)
    # Sole author last committed 240 days ago (> 180 days)
    records = [
        CommitChangeItem(
            commit_hash="c1",
            author_name="Dave Departed",
            author_email="dave@example.com",
            committed_at=now - timedelta(days=240),
            file_path="backend/legacy/billing.py",
            insertions=500,
            deletions=50,
        ),
    ]

    report = CodeOwnershipAnalyzer.analyze_ownership(
        target_files=["backend/legacy/billing.py"],
        commit_records=records,
        reference_time=now,
    )

    assert len(report.knowledge_loss_warnings) >= 1
    assert any(
        "Knowledge loss risk" in w and "Dave Departed" in w for w in report.knowledge_loss_warnings
    )


def test_diffused_ownership_warning():
    now = datetime.now(timezone.utc)
    # 4 authors, each making 1 commit with 50 insertions
    records = [
        CommitChangeItem(
            commit_hash=f"c{i}",
            author_name=f"Author {i}",
            author_email=f"author{i}@example.com",
            committed_at=now - timedelta(days=i),
            file_path="backend/shared/utils.py",
            insertions=50,
            deletions=0,
        )
        for i in range(1, 5)
    ]

    report = CodeOwnershipAnalyzer.analyze_ownership(
        target_files=["backend/shared/utils.py"],
        commit_records=records,
        reference_time=now,
    )

    fo = report.file_ownerships[0]
    assert fo.ownership_level == "DIFFUSED"
    assert any("Diffused ownership" in w for w in report.knowledge_loss_warnings)
