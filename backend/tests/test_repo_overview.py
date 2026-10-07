import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commit import Commit
from app.models.commit_file_change import ChangeType, CommitFileChange
from app.models.dependency import CodeDependency, DependencyKind
from app.models.design_constraint import ConstraintCategory, ConstraintLevel, DesignConstraint
from app.models.engineering_doc import EngineeringDocType, EngineeringDocument
from app.models.issue import Issue, IssueState
from app.models.pull_request import PullRequest, PullRequestState
from app.models.repository import Repository, RepositoryStatus
from app.models.source_file import SourceFile
from app.models.symbol import ArchitecturalRole, Symbol, SymbolKind
from app.overview.service import RepositoryOverviewService


@pytest.mark.asyncio
async def test_overview_empty_repo(db_session: AsyncSession):
    repo = Repository(
        id=uuid.uuid4(),
        owner="test-owner",
        name="empty-repo",
        full_name="test-owner/empty-repo",
        default_branch="main",
        status=RepositoryStatus.READY,
    )
    db_session.add(repo)
    await db_session.commit()

    overview = await RepositoryOverviewService.compute_overview(db_session, repo)
    assert overview.repository_id == repo.id
    assert overview.file_count == 0
    assert overview.symbol_count == 0
    assert overview.commit_count == 0
    assert overview.health.composite_score >= 80.0
    assert overview.health.status == "healthy"
    assert "test_protection" in overview.health.metrics
    assert "knowledge_distribution" in overview.health.metrics
    assert "defect_stability" in overview.health.metrics
    assert "architectural_modularity" in overview.health.metrics
    assert "governance" in overview.health.metrics
    assert "concurrent_activity" in overview.health.metrics


@pytest.mark.asyncio
async def test_overview_with_code_and_tests(db_session: AsyncSession):
    repo = Repository(
        id=uuid.uuid4(),
        owner="org",
        name="app-repo",
        full_name="org/app-repo",
        default_branch="main",
        status=RepositoryStatus.READY,
    )
    db_session.add(repo)
    await db_session.commit()

    # Source files
    sf1 = SourceFile(
        id=uuid.uuid4(),
        repository_id=repo.id,
        path="src/services/payment.ts",
        language="typescript",
        content_hash="h1",
        size_bytes=500,
    )
    sf2 = SourceFile(
        id=uuid.uuid4(),
        repository_id=repo.id,
        path="src/controllers/order.ts",
        language="typescript",
        content_hash="h2",
        size_bytes=600,
    )
    # Test file guarding sf1
    tf1 = SourceFile(
        id=uuid.uuid4(),
        repository_id=repo.id,
        path="tests/services/payment.test.ts",
        language="typescript",
        content_hash="h3",
        size_bytes=300,
    )
    db_session.add_all([sf1, sf2, tf1])

    # Symbols with architectural roles
    sym1 = Symbol(
        id=uuid.uuid4(),
        repository_id=repo.id,
        file_id=sf1.id,
        name="PaymentService",
        kind=SymbolKind.CLASS,
        line_start=1,
        line_end=50,
        architectural_role=ArchitecturalRole.SERVICE,
    )
    sym2 = Symbol(
        id=uuid.uuid4(),
        repository_id=repo.id,
        file_id=sf2.id,
        name="OrderController",
        kind=SymbolKind.CLASS,
        line_start=1,
        line_end=40,
        architectural_role=ArchitecturalRole.CONTROLLER,
    )
    db_session.add_all([sym1, sym2])

    # Dependency edge from tf1 to sf1
    dep = CodeDependency(
        id=uuid.uuid4(),
        repository_id=repo.id,
        source_file_id=tf1.id,
        source_path=tf1.path,
        target_path=sf1.path,
        kind=DependencyKind.INTERNAL,
    )

    db_session.add(dep)
    await db_session.commit()

    overview = await RepositoryOverviewService.compute_overview(db_session, repo)
    assert overview.file_count == 3
    assert overview.symbol_count == 2
    assert overview.dependency_count == 1
    assert overview.dominant_roles.get("service") == 1
    assert overview.dominant_roles.get("controller") == 1

    test_metric = overview.health.metrics["test_protection"]
    assert test_metric.details["total_test_files"] == 1
    assert test_metric.details["total_source_files"] == 2
    assert test_metric.details["covered_source_files"] == 1
    assert test_metric.details["untested_source_files"] == 1
    assert test_metric.score == 50.0
    assert test_metric.status == "warning"


@pytest.mark.asyncio
async def test_overview_with_history_and_hotspots(db_session: AsyncSession):
    repo = Repository(
        id=uuid.uuid4(),
        owner="org",
        name="churn-repo",
        full_name="org/churn-repo",
        default_branch="main",
        status=RepositoryStatus.READY,
    )
    db_session.add(repo)
    await db_session.commit()

    now = datetime.now(timezone.utc)
    # Commits: 2 regular, 2 defect fixes
    c1 = Commit(
        id=uuid.uuid4(),
        repository_id=repo.id,
        commit_hash="c111",
        message="feat: initial feature",
        author_name="Alice Dev",
        author_email="alice@example.com",
        committed_at=now,
        is_defect_fix=False,
    )
    c2 = Commit(
        id=uuid.uuid4(),
        repository_id=repo.id,
        commit_hash="c222",
        message="fix: resolve payment bug",
        author_name="Alice Dev",
        author_email="alice@example.com",
        committed_at=now,
        is_defect_fix=True,
    )
    c3 = Commit(
        id=uuid.uuid4(),
        repository_id=repo.id,
        commit_hash="c333",
        message="fix: resolve checkout crash",
        author_name="Bob Engineer",
        author_email="bob@example.com",
        committed_at=now,
        is_defect_fix=True,
    )
    db_session.add_all([c1, c2, c3])
    await db_session.flush()

    # File changes
    fc1 = CommitFileChange(
        id=uuid.uuid4(),
        commit_id=c1.id,
        file_path="src/checkout.ts",
        change_type=ChangeType.ADDED,
        insertions=100,
        deletions=0,
    )
    fc2 = CommitFileChange(
        id=uuid.uuid4(),
        commit_id=c2.id,
        file_path="src/checkout.ts",
        change_type=ChangeType.MODIFIED,
        insertions=10,
        deletions=5,
    )
    fc3 = CommitFileChange(
        id=uuid.uuid4(),
        commit_id=c3.id,
        file_path="src/checkout.ts",
        change_type=ChangeType.MODIFIED,
        insertions=15,
        deletions=2,
    )
    db_session.add_all([fc1, fc2, fc3])

    # PR and Issue
    pr = PullRequest(
        id=uuid.uuid4(),
        repository_id=repo.id,
        number=1,
        title="Payment update",
        author="alice",
        state=PullRequestState.OPEN,
    )
    issue = Issue(
        id=uuid.uuid4(),
        repository_id=repo.id,
        number=10,
        title="Checkout failure",
        author="alice",
        state=IssueState.OPEN,
    )
    db_session.add_all([pr, issue])

    # ADR & Invariant
    adr = EngineeringDocument(
        id=uuid.uuid4(),
        repository_id=repo.id,
        path="docs/adr/001-payment.md",
        title="ADR 001 Payment",
        doc_type=EngineeringDocType.ADR,
        raw_content="# ADR 1",
        content_hash="hadr001",
    )

    constraint = DesignConstraint(
        id=uuid.uuid4(),
        repository_id=repo.id,
        document_id=adr.id,
        category=ConstraintCategory.SECURITY,
        level=ConstraintLevel.MUST,
        title="Payment Token Encryption",
        statement="Payment tokens MUST be encrypted",
        source_path="docs/adr/001-payment.md",
    )
    db_session.add_all([adr, constraint])

    await db_session.commit()

    overview = await RepositoryOverviewService.compute_overview(db_session, repo)
    assert overview.commit_count == 3
    assert overview.pull_request_count == 1
    assert overview.issue_count == 1
    assert overview.adr_count == 1
    assert overview.constraint_count == 1

    # Hotspot verification
    assert len(overview.hotspots) >= 1
    hotspot = overview.hotspots[0]
    assert hotspot.file_path == "src/checkout.ts"
    assert hotspot.change_count == 3
    assert hotspot.defect_count == 2
    assert hotspot.risk_level in ["high", "medium"]

    # Contributors verification
    assert len(overview.top_contributors) == 2
    top_author = overview.top_contributors[0]
    assert top_author.name == "Alice Dev"
    assert top_author.commit_count == 2
    assert top_author.role == "Lead Maintainer"

    # Defect stability metric
    defect_metric = overview.health.metrics["defect_stability"]
    assert defect_metric.details["defect_commits"] == 2
    assert defect_metric.status == "alert"  # 2 out of 3 = 67% defect ratio

    # Governance metric
    gov_metric = overview.health.metrics["governance"]
    assert gov_metric.status in ["healthy", "warning"]


@pytest.mark.asyncio
async def test_overview_api_endpoint(client: AsyncClient, db_session: AsyncSession):
    repo = Repository(
        id=uuid.uuid4(),
        owner="api-test",
        name="web-service",
        full_name="api-test/web-service",
        default_branch="main",
        status=RepositoryStatus.READY,
    )
    db_session.add(repo)
    await db_session.commit()

    response = await client.get(f"/api/v1/repositories/{repo.id}/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["repository_id"] == str(repo.id)
    assert data["name"] == "web-service"
    assert "health" in data
    assert data["health"]["composite_score"] > 0
    assert "metrics" in data["health"]
    assert "test_protection" in data["health"]["metrics"]
    assert "knowledge_distribution" in data["health"]["metrics"]
    assert "defect_stability" in data["health"]["metrics"]
    assert "architectural_modularity" in data["health"]["metrics"]
    assert "governance" in data["health"]["metrics"]
    assert "concurrent_activity" in data["health"]["metrics"]
