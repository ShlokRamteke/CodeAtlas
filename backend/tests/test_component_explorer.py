import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repository import Repository, RepositoryStatus
from app.models.source_file import SourceFile
from app.models.symbol import ArchitecturalRole, Symbol, SymbolKind
from app.parser.ast_parser import ExtractedDependency, ExtractedSymbol, ParsedFileResult
from app.parser.relationship_analyzer import RelationshipAnalyzer


def test_relationship_analyzer_component_enrichment():
    parsed_files = [
        ParsedFileResult(
            path="src/controllers/user_controller.py",
            language="python",
            symbols=[
                ExtractedSymbol(
                    name="UserController",
                    kind="class",
                    line_start=1,
                    line_end=50,
                    architectural_role="controller",
                ),
                ExtractedSymbol(
                    name="get_users",
                    kind="function",
                    line_start=10,
                    line_end=20,
                    architectural_role="controller",
                ),
            ],
            dependencies=[
                ExtractedDependency(
                    target_path="src/services/user_service.py",
                    kind="internal",
                )
            ],
        ),
        ParsedFileResult(
            path="src/services/user_service.py",
            language="python",
            symbols=[
                ExtractedSymbol(
                    name="UserService",
                    kind="class",
                    line_start=1,
                    line_end=40,
                    architectural_role="service",
                )
            ],
            dependencies=[],
        ),
        ParsedFileResult(
            path="tests/test_user_service.py",
            language="python",
            symbols=[
                ExtractedSymbol(
                    name="test_get_users",
                    kind="function",
                    line_start=1,
                    line_end=15,
                )
            ],
            dependencies=[],
        ),
    ]

    analyzer = RelationshipAnalyzer()
    graph = analyzer.analyze_repository(parsed_files)

    comp_map = {c.path: c for c in graph.major_components}
    assert "src/controllers" in comp_map
    assert "src/services" in comp_map

    ctrl_comp = comp_map["src/controllers"]
    assert ctrl_comp.dominant_role == "controller"
    assert ctrl_comp.symbol_roles.get("controller") == 2
    assert "src/controllers/user_controller.py" in ctrl_comp.files
    assert ctrl_comp.test_coverage_status == "untested"

    svc_comp = comp_map["src/services"]
    assert svc_comp.dominant_role == "service"
    assert "src/controllers" in svc_comp.inbound_callers
    assert svc_comp.test_coverage_status == "guarded"
    assert svc_comp.tested_by == "tests/test_user_service.py"


@pytest.mark.asyncio
async def test_get_repository_architecture_enriched(client: AsyncClient, db_session: AsyncSession):
    repo = Repository(
        id=uuid.uuid4(),
        owner="acme",
        name="store",
        full_name="acme/store",
        default_branch="main",
        status=RepositoryStatus.READY,
    )
    db_session.add(repo)
    await db_session.flush()

    f1 = SourceFile(
        id=uuid.uuid4(),
        repository_id=repo.id,
        path="src/services/payment.ts",
        language="typescript",
        content_hash="abc1",
        size_bytes=100,
    )
    f2 = SourceFile(
        id=uuid.uuid4(),
        repository_id=repo.id,
        path="src/services/payment.test.ts",
        language="typescript",
        content_hash="abc2",
        size_bytes=80,
    )
    db_session.add_all([f1, f2])
    await db_session.flush()

    s1 = Symbol(
        id=uuid.uuid4(),
        file_id=f1.id,
        repository_id=repo.id,
        name="processPayment",
        kind=SymbolKind.FUNCTION,
        line_start=10,
        line_end=30,
        architectural_role=ArchitecturalRole.SERVICE,
    )
    db_session.add(s1)
    await db_session.commit()

    resp = await client.get(f"/api/v1/repositories/{repo.id}/architecture")
    assert resp.status_code == 200
    data = resp.json()

    assert data["repository_id"] == str(repo.id)
    assert len(data["major_components"]) > 0
    svc_comp = next((c for c in data["major_components"] if c["path"] == "src/services"), None)
    assert svc_comp is not None
    assert svc_comp["dominant_role"] == "service"
    assert svc_comp["test_coverage_status"] == "guarded"
    assert "src/services/payment.ts" in svc_comp["files"]


@pytest.mark.asyncio
async def test_get_component_detail_endpoint(client: AsyncClient, db_session: AsyncSession):
    repo = Repository(
        id=uuid.uuid4(),
        owner="acme",
        name="billing",
        full_name="acme/billing",
        default_branch="main",
        status=RepositoryStatus.READY,
    )
    db_session.add(repo)
    await db_session.flush()

    f1 = SourceFile(
        id=uuid.uuid4(),
        repository_id=repo.id,
        path="src/billing/invoice.py",
        language="python",
        content_hash="inv1",
        size_bytes=150,
    )
    db_session.add(f1)
    await db_session.flush()

    s1 = Symbol(
        id=uuid.uuid4(),
        file_id=f1.id,
        repository_id=repo.id,
        name="InvoiceGenerator",
        kind=SymbolKind.CLASS,
        line_start=1,
        line_end=50,
        signature="class InvoiceGenerator:",
        architectural_role=ArchitecturalRole.SERVICE,
    )
    db_session.add(s1)
    await db_session.commit()

    # Success case
    resp = await client.get(f"/api/v1/repositories/{repo.id}/components/src/billing/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "src > billing"
    assert data["path"] == "src/billing"
    assert data["dominant_role"] == "service"
    assert len(data["symbols"]) == 1
    assert data["symbols"][0]["name"] == "InvoiceGenerator"
    assert data["symbols"][0]["file_path"] == "src/billing/invoice.py"
    assert "src/billing/invoice.py" in data["files"]

    # 404 for non-existent component
    not_found = await client.get(f"/api/v1/repositories/{repo.id}/components/non/existent/overview")
    assert not_found.status_code == 404
