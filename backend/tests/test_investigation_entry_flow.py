from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dependency import CodeDependency
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.models.source_file import SourceFile
from app.models.symbol import ArchitecturalRole, Symbol, SymbolKind


@pytest.mark.asyncio
async def test_investigation_entry_flow_endpoints(
    db_session: AsyncSession,
    client: AsyncClient,
) -> None:
    # 1. Create Repository
    repo_id = uuid.uuid4()
    repo = Repository(
        id=repo_id,
        owner="saas-org",
        name="entry-flow-repo",
        full_name="saas-org/entry-flow-repo",
        default_branch="main",
    )
    db_session.add(repo)
    await db_session.flush()

    # 2. Add SourceFiles
    f1_id = uuid.uuid4()
    f1 = SourceFile(
        id=f1_id,
        repository_id=repo_id,
        path="src/controllers/auth_controller.py",
        language="python",
        content_hash="h1",
        size_bytes=1200,
    )
    f2_id = uuid.uuid4()
    f2 = SourceFile(
        id=f2_id,
        repository_id=repo_id,
        path="src/services/auth_service.py",
        language="python",
        content_hash="h2",
        size_bytes=2400,
    )
    f_test_id = uuid.uuid4()
    f_test = SourceFile(
        id=f_test_id,
        repository_id=repo_id,
        path="tests/test_auth_service.py",
        language="python",
        content_hash="h3",
        size_bytes=800,
    )
    db_session.add_all([f1, f2, f_test])
    await db_session.flush()

    # 3. Add Symbols
    s1 = Symbol(
        id=uuid.uuid4(),
        file_id=f1_id,
        repository_id=repo_id,
        name="login_endpoint",
        kind=SymbolKind.FUNCTION,
        line_start=10,
        line_end=25,
        signature="def login_endpoint(req: LoginRequest) -> TokenResponse",
        architectural_role=ArchitecturalRole.CONTROLLER,
    )
    s2 = Symbol(
        id=uuid.uuid4(),
        file_id=f2_id,
        repository_id=repo_id,
        name="AuthService",
        kind=SymbolKind.CLASS,
        line_start=5,
        line_end=80,
        signature="class AuthService",
        architectural_role=ArchitecturalRole.SERVICE,
    )
    db_session.add_all([s1, s2])
    await db_session.flush()

    # 4. Add Code Dependencies
    # auth_controller imports auth_service
    # test_auth_service imports auth_service
    dep1 = CodeDependency(
        id=uuid.uuid4(),
        repository_id=repo_id,
        source_file_id=f1_id,
        source_path="src/controllers/auth_controller.py",
        target_path="src/services/auth_service.py",
        kind="internal",
    )
    dep2 = CodeDependency(
        id=uuid.uuid4(),
        repository_id=repo_id,
        source_file_id=f_test_id,
        source_path="tests/test_auth_service.py",
        target_path="src/services/auth_service.py",
        kind="internal",
    )
    db_session.add_all([dep1, dep2])

    # 5. Add an in-flight open Pull Request touching auth_service.py
    pr = PullRequest(
        id=uuid.uuid4(),
        repository_id=repo_id,
        number=42,
        title="feat(auth): add OAuth2 refresh token rotation",
        body="Upgrades session refresh tokens",
        state="open",
        author="alice",
        head_branch="feat/oauth2-refresh",
        base_branch="main",
        touched_files=["src/services/auth_service.py"],
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(pr)
    await db_session.commit()

    # TEST 1: GET /api/v1/repositories/{id}/files
    res_files = await client.get(f"/api/v1/repositories/{repo_id}/files")
    assert res_files.status_code == 200
    files_data = res_files.json()
    assert len(files_data) == 3
    paths = {f["path"]: f["symbol_count"] for f in files_data}
    assert "src/controllers/auth_controller.py" in paths
    assert paths["src/controllers/auth_controller.py"] == 1
    assert "src/services/auth_service.py" in paths
    assert paths["src/services/auth_service.py"] == 1

    # TEST 2: GET /api/v1/repositories/{id}/symbols (with file_path)
    res_symbols = await client.get(f"/api/v1/repositories/{repo_id}/symbols")
    assert res_symbols.status_code == 200
    syms_data = res_symbols.json()
    assert len(syms_data) == 2
    sym_map = {s["name"]: s for s in syms_data}
    assert "login_endpoint" in sym_map
    assert sym_map["login_endpoint"]["file_path"] == "src/controllers/auth_controller.py"
    assert sym_map["login_endpoint"]["architectural_role"] == "controller"
    assert "AuthService" in sym_map
    assert sym_map["AuthService"]["file_path"] == "src/services/auth_service.py"
    assert sym_map["AuthService"]["architectural_role"] == "service"

    # TEST 3: POST /api/v1/investigations/preview-impact
    preview_payload = {
        "repository_id": str(repo_id),
        "target_files": ["src/services/auth_service.py"],
        "query": "Refactor AuthService session validation",
    }
    res_preview = await client.post("/api/v1/investigations/preview-impact", json=preview_payload)
    assert res_preview.status_code == 200
    preview_data = res_preview.json()

    # Check targets & normalized intent
    assert "src/services/auth_service.py" in preview_data["target_files"]
    assert "refactor" in preview_data["normalized_intent"]["action_verbs"]

    # Check Blast Radius (auth_controller is upstream caller)
    blast = preview_data["blast_radius"]
    assert blast["total_affected_count"] >= 1
    upstream_paths = [u["path"] for u in blast.get("upstream_callers", [])]
    assert "src/controllers/auth_controller.py" in upstream_paths

    # Check Guarding Tests (tests/test_auth_service.py covers auth_service)
    guarding = preview_data["guarding_tests"]
    assert guarding["total_guarding_tests"] >= 1
    ranked_test_files = [t["test_file"] for t in guarding.get("ranked_tests", [])]
    assert "tests/test_auth_service.py" in ranked_test_files

    # Check Concurrent Overlaps (PR #42 is detected as collision!)
    overlaps = preview_data["concurrent_overlaps"]
    assert overlaps["overlapping_pr_count"] >= 1
    pr_numbers = [p["pr_number"] for p in overlaps.get("overlapping_prs", [])]
    assert 42 in pr_numbers
