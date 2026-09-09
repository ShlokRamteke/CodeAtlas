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
        {
            "id": "s1",
            "file_id": "f1",
            "name": "PaymentService",
            "kind": "class",
            "signature": "class PaymentService",
            "line_start": 1,
            "line_end": 20,
        },
        {
            "id": "s2",
            "file_id": "f1",
            "name": "charge",
            "kind": "method",
            "signature": "async charge()",
            "line_start": 10,
            "line_end": 15,
        },
    ]
    dependencies = [
        {
            "source_file_id": "f1",
            "source_path": "src/services/PaymentService.ts",
            "target_path": "../models/User",
            "imported_symbol": "User",
            "kind": "relative",
            "confidence": 1.0,
        },
    ]
    relationships = [
        {
            "source_name": "CheckoutService",
            "source_path": "src/services/CheckoutService.ts",
            "target_name": "PaymentService",
            "target_path": "src/services/PaymentService.ts",
            "type": "imports",
            "confidence": 1.0,
            "resolution_method": "tree_sitter_ast",
        },
        {
            "source_name": "PaymentService",
            "source_path": "src/services/PaymentService.ts",
            "target_name": "PaymentService.test",
            "target_path": "src/services/PaymentService.test.ts",
            "type": "tested_by",
            "confidence": 0.90,
            "resolution_method": "filename_heuristic",
        },
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
        {
            "id": "s1",
            "file_id": "f1",
            "name": "doSomethingUnchecked",
            "kind": "function",
            "signature": "function doSomethingUnchecked()",
            "line_start": 1,
            "line_end": 5,
        },
    ]
    dependencies = [
        {
            "source_file_id": "f1",
            "source_path": "src/legacy/orphan_module.ts",
            "target_path": "external-unknown-pkg",
            "kind": "external",
            "confidence": 1.0,
        },
    ]
    relationships = [
        {
            "source_name": "orphan_module",
            "source_path": "src/legacy/orphan_module.ts",
            "target_name": "mystery_target",
            "target_path": "src/mystery.ts",
            "type": "calls",
            "confidence": 0.50,
            "resolution_method": "fuzzy_name_match",
        },
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
        {
            "id": "s_py",
            "file_id": "py1",
            "name": "AnalyticsEngine",
            "kind": "class",
            "signature": "class AnalyticsEngine:",
            "line_start": 4,
            "line_end": 20,
        },
        {
            "id": "s_ts",
            "file_id": "ts1",
            "name": "UserPayload",
            "kind": "interface",
            "signature": "interface UserPayload",
            "line_start": 1,
            "line_end": 6,
        },
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


def test_project_context_historical_and_engineering_enrichment() -> None:
    """Verify canonical ProjectContext enrichment with git history, PRs, issues, ADRs, and RFC 2119 invariants."""
    from app.context_builder.builder import ProjectContextBuilder
    from app.schemas.repository import ProjectContextRead

    builder = ProjectContextBuilder()

    files = [
        {"id": "f_checkout", "path": "src/checkout/handler.ts", "language": "typescript"},
        {"id": "f_payment", "path": "src/services/stripe.ts", "language": "typescript"},
    ]
    symbols = [
        {
            "id": "s_checkout",
            "file_id": "f_checkout",
            "name": "handleCheckout",
            "kind": "function",
            "signature": "function handleCheckout(cartId: string): Promise<Order>",
            "line_start": 5,
            "line_end": 25,
        },
        {
            "id": "s_payment",
            "file_id": "f_payment",
            "name": "StripeClient",
            "kind": "class",
            "signature": "class StripeClient",
            "line_start": 1,
            "line_end": 40,
        },
    ]
    dependencies = [
        {
            "source_file_id": "f_checkout",
            "source_path": "src/checkout/handler.ts",
            "target_path": "../services/stripe",
            "imported_symbol": "StripeClient",
            "kind": "relative",
            "confidence": 1.0,
        }
    ]
    relationships = [
        {
            "source_name": "handleCheckout",
            "source_path": "src/checkout/handler.ts",
            "target_name": "StripeClient",
            "target_path": "src/services/stripe.ts",
            "type": "calls",
            "confidence": 1.0,
            "resolution_method": "tree_sitter_ast",
        }
    ]

    historical_changes = [
        {
            "commit_hash": "a1b2c3d4e5f60001",
            "message": "feat: introduce stripe payment integration",
            "author": "Alice Dev",
            "committed_at": "2026-01-10T10:00:00Z",
            "change_type": "added",
            "files_changed": ["src/services/stripe.ts"],
            "is_introducing": True,
            "pr_number": 10,
        },
        {
            "commit_hash": "b2c3d4e5f6a10002",
            "message": "fix: sanitize checkout cart before charging",
            "author": "Bob Sec",
            "committed_at": "2026-02-15T12:00:00Z",
            "change_type": "modified",
            "files_changed": ["src/checkout/handler.ts", "src/services/stripe.ts"],
            "is_introducing": False,
            "pr_number": 15,
        },
    ]

    related_prs = [
        {
            "pr_number": 10,
            "title": "Introduce Stripe payment integration",
            "state": "merged",
            "author": "Alice Dev",
            "merged_at": "2026-01-10T11:00:00Z",
            "url": "https://github.com/example/repo/pull/10",
            "linked_issue_numbers": [42],
        },
        {
            "pr_number": 15,
            "title": "Sanitize checkout cart input",
            "state": "merged",
            "author": "Bob Sec",
            "merged_at": "2026-02-15T13:00:00Z",
            "url": "https://github.com/example/repo/pull/15",
            "linked_issue_numbers": [45],
        },
    ]

    related_issues = [
        {
            "issue_number": 42,
            "title": "Support credit card payments via Stripe",
            "state": "closed",
            "author": "Product Lead",
            "closed_at": "2026-01-10T11:05:00Z",
            "labels": ["feature", "payments"],
            "url": "https://github.com/example/repo/issues/42",
        },
        {
            "issue_number": 45,
            "title": "Security vulnerability in cart validation",
            "state": "closed",
            "author": "Security Auditor",
            "closed_at": "2026-02-15T13:10:00Z",
            "labels": ["security", "bug"],
            "url": "https://github.com/example/repo/issues/45",
        },
    ]

    documents = [
        {
            "id": "doc-adr-004",
            "path": "docs/decisions/ADR-004-stripe-payments.md",
            "title": "ADR-004: Standardize on Stripe for Payment Processing",
            "doc_type": "adr",
            "status": "accepted",
            "deciders": "Alice, Bob, Tech Lead",
            "summary": "Standardize all checkout transactions on Stripe SDK with webhook signature validation.",
        }
    ]

    design_constraints = [
        {
            "id": "dc-sec-01",
            "domain": "security",
            "constraint_text": "Never log or persist raw credit card credentials or CVV codes.",
            "source_doc_path": "docs/decisions/ADR-004-stripe-payments.md",
            "priority": "MUST_NOT",
        },
        {
            "id": "dc-arch-01",
            "domain": "architecture",
            "constraint_text": "All checkout payment operations MUST route through StripeClient adapter.",
            "source_doc_path": "docs/decisions/ADR-004-stripe-payments.md",
            "priority": "MUST",
        },
    ]

    context = builder.build_project_context(
        target_id="repo-enrich",
        target_name="demo/checkout-system",
        target_type="repository",
        files=files,
        symbols=symbols,
        dependencies=dependencies,
        relationships=relationships,
        historical_changes=historical_changes,
        related_prs=related_prs,
        related_issues=related_issues,
        documents=documents,
        design_constraints=design_constraints,
    )

    # 1. Multi-source Provenance
    assert "tree_sitter_ast" in context.provenance
    assert "git_history" in context.provenance
    assert "github_provenance" in context.provenance
    assert "engineering_docs" in context.provenance

    # 2. Entity Historical & Architectural Attachments
    file_entities = {e.path: e for e in context.entities if e.kind == "file"}
    stripe_file = file_entities["src/services/stripe.ts"]
    assert stripe_file.introducing_commit == "a1b2c3d4e5f60001"
    assert stripe_file.change_count == 2
    assert "Alice Dev" in stripe_file.active_authors
    assert "Bob Sec" in stripe_file.active_authors
    assert any("ADR-004" in adr for adr in stripe_file.related_adrs)

    # 3. Historical changes, PRs, and Issues
    assert len(context.historical_changes) == 2
    assert context.historical_changes[0].commit_hash == "b2c3d4e5f6a10002"  # Chronological desc
    assert len(context.related_prs) == 2
    assert context.related_prs[0].pr_number == 10
    assert len(context.related_issues) == 2
    assert context.related_issues[0].issue_number == 42

    # 4. Engineering Documents & ADR constraints
    assert len(context.documents) == 1
    assert context.documents[0].status == "accepted"
    assert len(context.design_constraints) == 2
    assert any(dc.priority == "MUST_NOT" for dc in context.design_constraints)

    # 5. Multi-source Evidence Records
    evidence_kinds = {e.kind for e in context.evidence}
    assert "ast_symbol" in evidence_kinds
    assert "git_commit" in evidence_kinds
    assert "pull_request" in evidence_kinds
    assert "architecture_decision" in evidence_kinds
    assert "design_constraint" in evidence_kinds

    # 6. Human Markdown Projections
    human_md = context.to_human_markdown()
    assert "Historical Evolution" in human_md
    assert "Provenance Traces" in human_md
    assert "Engineering Context" in human_md
    assert "Architectural Invariants & Constraints" in human_md
    assert "ADR-004" in human_md
    assert "MUST_NOT" in human_md

    # 7. Token-Budgeted LLM Prompt Projections
    llm_prompt = context.to_llm_prompt()
    assert "RECENT_HISTORY" in llm_prompt
    assert "LINKED_PRS_ISSUES" in llm_prompt
    assert "ADRS_DOCS" in llm_prompt
    assert "DESIGN_CONSTRAINTS" in llm_prompt

    # 8. REST Serialization & Validation
    serialized = context.to_dict()
    validated = ProjectContextRead.model_validate(serialized)
    assert len(validated.historical_changes) == 2
    assert len(validated.documents) == 1
    assert len(validated.design_constraints) == 2


@pytest.mark.asyncio
async def test_api_get_repository_context_enriched_integration(client: AsyncClient) -> None:
    """Integration test verifying GET /context endpoint returns unified AST + Git + Docs context."""
    # 1. Create repository
    create_res = await client.post(
        "/api/v1/repositories/",
        json={"owner": "full-test", "name": "unified-repo", "full_name": "full-test/unified-repo"},
    )
    assert create_res.status_code == 201
    repo_id = create_res.json()["id"]

    # 2. Ingest code files
    await client.post(
        f"/api/v1/repositories/{repo_id}/ingest",
        json={
            "files": {
                "src/payment.ts": "export class PaymentProcessor { charge() { return true; } }",
            }
        },
    )

    # 3. Ingest commit history
    ingest_commit_res = await client.post(
        f"/api/v1/repositories/{repo_id}/commits/ingest",
        json={
            "commits": [
                {
                    "commit_hash": "c0ffee1234567890",
                    "message": "feat: initial payment processor implementation",
                    "author_name": "Lead Dev",
                    "author_email": "lead@example.com",
                    "committed_at": "2026-03-01T12:00:00Z",
                    "file_changes": [
                        {"file_path": "src/payment.ts", "change_type": "added", "insertions": 10, "deletions": 0}
                    ],
                }
            ]
        },
    )
    assert ingest_commit_res.status_code == 200

    # 4. Ingest engineering documentation
    ingest_doc_res = await client.post(
        f"/api/v1/repositories/{repo_id}/engineering/ingest",
        json={
            "files": {
                "docs/decisions/ADR-001-payment-engine.md": """# ADR-001: Payment Engine Invariants

## Status
Accepted

## Context
Payment processing must be idempotent and safe.

## Consequences
The system MUST verify idempotent transaction keys before charging.
The system MUST NOT persist raw credentials in logs.
"""
            }
        },
    )
    assert ingest_doc_res.status_code == 201

    # 5. Query canonical /context endpoint
    ctx_res = await client.get(f"/api/v1/repositories/{repo_id}/context")
    assert ctx_res.status_code == 200
    data = ctx_res.json()

    assert data["target_type"] == "repository"
    assert "tree_sitter_ast" in data["provenance"]
    assert "git_history" in data["provenance"]
    assert "engineering_docs" in data["provenance"]

    # Check entities have historical data attached
    payment_entity = next(e for e in data["entities"] if e["path"] == "src/payment.ts")
    assert payment_entity["introducing_commit"] == "c0ffee1234567890"
    assert payment_entity["change_count"] == 1

    # Check historical changes and documents
    assert len(data["historical_changes"]) >= 1
    assert data["historical_changes"][0]["commit_hash"] == "c0ffee1234567890"
    assert len(data["documents"]) >= 1
    assert data["documents"][0]["title"] == "ADR-001: Payment Engine Invariants"
    assert len(data["design_constraints"]) >= 2

