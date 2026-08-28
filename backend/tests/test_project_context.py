from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.context_builder.builder import CurrentSystemContextBuilder
from app.context_builder.project_context import ProjectContext


def test_canonical_project_context_structure() -> None:
    builder = CurrentSystemContextBuilder()

    files = [
        {"id": "f1", "path": "src/services/PaymentService.ts", "language": "typescript"},
        {"id": "f2", "path": "src/services/PaymentService.test.ts", "language": "typescript"},
    ]
    symbols = [
        {"id": "s1", "file_id": "f1", "name": "PaymentService", "kind": "class", "signature": "class PaymentService", "line_start": 1, "line_end": 20},
        {"id": "s2", "file_id": "f1", "name": "charge", "kind": "method", "signature": "async charge()", "line_start": 10, "line_end": 15},
    ]
    dependencies = [
        {"source_file_id": "f1", "source_path": "src/services/PaymentService.ts", "target_path": "../models/User", "imported_symbol": "User", "kind": "relative", "confidence": 1.0},
    ]
    relationships = [
        {"source_name": "CheckoutService", "source_path": "src/services/CheckoutService.ts", "target_name": "PaymentService", "target_path": "src/services/PaymentService.ts", "type": "imports", "confidence": 1.0, "resolution_method": "tree_sitter_ast"},
        {"source_name": "PaymentService", "source_path": "src/services/PaymentService.ts", "target_name": "PaymentService.test", "target_path": "src/services/PaymentService.test.ts", "type": "tested_by", "confidence": 0.90, "resolution_method": "filename_heuristic"},
    ]

    context: ProjectContext = builder.build_project_context(
        target_id="repo-1",
        target_name="demo/payment-service",
        target_type="repository",
        files=files,
        symbols=symbols,
        dependencies=dependencies,
        relationships=relationships,
    )

    # 1. Core Metadata
    assert context.target_name == "demo/payment-service"
    assert context.target_type == "repository"
    assert context.confidence > 0.8
    assert context.provenance == "tree_sitter_ast"

    # 2. Entities
    assert len(context.entities) == 4  # 2 files + 2 symbols
    symbol_entities = [e for e in context.entities if e.kind == "symbol"]
    assert len(symbol_entities) == 2
    assert symbol_entities[0].name == "PaymentService"

    # 3. Canonical Relationships
    assert len(context.relationships) == 2
    assert any(r.type == "tested_by" for r in context.relationships)
    assert any(r.type == "imports" for r in context.relationships)

    # 4. Evidence Records
    assert len(context.evidence) > 0
    assert any(e.kind == "ast_symbol" for e in context.evidence)
    assert any(e.kind == "test_binding" for e in context.evidence)

    # 5. Dual Projections from ONE Context
    human_md = context.to_human_markdown()
    llm_prompt = context.to_llm_prompt()

    assert "PaymentService" in human_md
    assert "Grounded Evidence Records" in human_md
    assert "UNIFIED PROJECT CONTEXT BRIEFING" in llm_prompt
    assert "PaymentService" in llm_prompt


def test_project_context_incomplete_and_uncertain_data() -> None:
    """Test handling of untested code, unresolved external dependencies, empty files, and low confidence."""
    builder = CurrentSystemContextBuilder()

    files = [
        {"id": "f1", "path": "src/legacy/orphan_module.ts", "language": "typescript"},
        {"id": "f2", "path": "src/empty/empty_file.ts", "language": "typescript"},
    ]
    symbols = [
        {"id": "s1", "file_id": "f1", "name": "doSomethingUnchecked", "kind": "function", "signature": "function doSomethingUnchecked()", "line_start": 1, "line_end": 5},
    ]
    dependencies = [
        {"source_file_id": "f1", "source_path": "src/legacy/orphan_module.ts", "target_path": "external-unknown-pkg", "kind": "external", "confidence": 1.0},
    ]
    relationships = [
        {"source_name": "orphan_module", "source_path": "src/legacy/orphan_module.ts", "target_name": "mystery_target", "target_path": "src/mystery.ts", "type": "calls", "confidence": 0.50, "resolution_method": "fuzzy_name_match"},
    ]

    context = builder.build_project_context(
        target_id="repo-2",
        target_name="demo/incomplete-repo",
        target_type="repository",
        files=files,
        symbols=symbols,
        dependencies=dependencies,
        relationships=relationships,
    )

    # Verify Unknowns detection
    unknown_kinds = [u.kind for u in context.unknowns]
    assert "untested" in unknown_kinds  # orphan_module has no test
    assert "unresolved_dependency" in unknown_kinds  # external-unknown-pkg
    assert "empty_file" in unknown_kinds  # empty_file.ts has no symbols
    assert "low_confidence" in unknown_kinds  # 0.50 fuzzy match

    # Verify confidence was penalized by low-confidence relationship
    assert context.confidence == 0.50
    assert "Unknowns & Uncertainties" in context.to_human_markdown()
    assert "UNKNOWNS_GAPS" in context.to_llm_prompt()


def test_project_context_multiple_entity_types_and_languages() -> None:
    """Test Python + TypeScript multi-entity contexts."""
    builder = CurrentSystemContextBuilder()

    files = [
        {"id": "py1", "path": "app/services/analytics.py", "language": "python"},
        {"id": "ts1", "path": "src/types/models.ts", "language": "typescript"},
    ]
    symbols = [
        {"id": "s_py", "file_id": "py1", "name": "AnalyticsEngine", "kind": "class", "signature": "class AnalyticsEngine:", "line_start": 4, "line_end": 20},
        {"id": "s_ts", "file_id": "ts1", "name": "UserPayload", "kind": "interface", "signature": "interface UserPayload", "line_start": 1, "line_end": 6},
    ]

    context = builder.build_project_context(
        target_id="repo-3",
        target_name="demo/polyglot-repo",
        target_type="repository",
        files=files,
        symbols=symbols,
        dependencies=[],
        relationships=[],
    )

    assert len(context.entities) == 4
    kinds = {e.kind for e in context.entities}
    assert "file" in kinds
    assert "symbol" in kinds


@pytest.mark.asyncio
async def test_api_get_repository_context_endpoint(client: AsyncClient) -> None:
    """Integration test for GET /api/v1/repositories/{id}/context."""
    # 1. Create repo
    create_res = await client.post(
        "/api/v1/repositories/",
        json={"owner": "context-test", "name": "ctx-repo", "full_name": "context-test/ctx-repo"},
    )
    assert create_res.status_code == 201
    repo_id = create_res.json()["id"]

    # 2. Ingest code
    await client.post(
        f"/api/v1/repositories/{repo_id}/ingest",
        json={
            "files": {
                "src/auth.ts": "export class Auth { login() { return true; } }",
                "src/auth.test.ts": "import { Auth } from './auth';",
            }
        },
    )

    # 3. Query canonical ProjectContext endpoint
    ctx_res = await client.get(f"/api/v1/repositories/{repo_id}/context")
    assert ctx_res.status_code == 200
    data = ctx_res.json()

    assert data["target_type"] == "repository"
    assert data["target_name"] == "context-test/ctx-repo"
    assert len(data["entities"]) >= 2
    assert len(data["relationships"]) >= 1
    assert "human_markdown" in data
    assert "llm_prompt_context" in data
    assert "Auth" in data["human_markdown"]

