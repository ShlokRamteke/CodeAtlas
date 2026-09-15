from app.context_builder.project_context import (
    ContextDesignConstraint,
    ContextEntity,
    ContextEvidence,
    ContextHistoricalChange,
    ContextRelationship,
    ProjectContext,
)
from app.investigation.distillation import (
    OmissionRegistry,
    TokenBudgetDistiller,
    estimate_json_tokens,
    estimate_tokens,
)
from app.investigation.state import ClaimClassification, InvestigationClaim, PreChangeBrief


def test_token_estimation_heuristics():
    assert estimate_tokens("") == 0
    assert estimate_tokens("hello world") > 0
    assert estimate_json_tokens(None) == 0

    code_snippet = """
    def process_payment(user_id: str, amount: float) -> bool:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        return gateway.charge(user_id, amount)
    """
    est = estimate_tokens(code_snippet)
    assert 20 <= est <= 60

    json_data = {"key": "value", "list": [1, 2, 3], "nested": {"a": True}}
    json_est = estimate_json_tokens(json_data)
    assert json_est > 0


def test_omission_registry():
    registry = OmissionRegistry()
    marker = registry.register(
        ref_id="ref#test-01",
        marker_type="test",
        title="Payment Gateway Integration Test",
        summary="Tests multi-currency payment charging and webhooks",
        original_payload={"path": "tests/test_payment.py", "reach": 3},
    )

    assert marker.ref_id == "ref#test-01"
    assert registry.get("ref#test-01") == marker
    assert registry.get("ref#unknown") is None
    assert len(registry.all_markers()) == 1

    dense = marker.to_dense_json()
    assert dense["_omitted"] is True
    assert dense["ref"] == "ref#test-01"
    assert marker.to_markdown_tag() == "`[ref#test-01]` *(Payment Gateway Integration Test)*"

    registry.clear()
    assert len(registry.all_markers()) == 0


def test_pre_change_brief_distillation_unconstrained():
    registry = OmissionRegistry()
    brief_data = {
        "summary": "Proposed refactoring of payment gateway adapter",
        "intent_summary": "Refactor payment adapter for Stripe",
        "target_files": ["app/payments/gateway.py"],
        "target_symbols": ["PaymentGateway"],
        "claims": [
            {
                "id": "cl-1",
                "classification": "fact",
                "statement": "Target file handles credit card charges",
            },
        ],
        "signals": {
            "change_risk": {
                "risk_score": 0.35,
                "risk_level": "LOW",
                "shannon_entropy": 0.8,
                "defect_pressure": 0.1,
                "kamei_metrics": {"lines_added": 25, "lines_deleted": 10, "files_touched": 1},
            },
            "guarding_tests": {
                "untested_files": [],
                "ranked_tests": [{"test_file": "tests/test_gateway.py", "reached_target_count": 1}],
            },
            "blast_radius": {
                "affected_components": ["billing"],
                "upstream_callers": [{"path": "app/services/checkout.py", "depth": 1}],
            },
        },
        "constraints": [
            {
                "id": "inv-01",
                "title": "PCI Compliance Invariant",
                "statement": "Never log raw card details",
                "level": "must",
                "governing_status": "governing",
            }
        ],
        "recommended_checks": ["Run tests/test_gateway.py before merging"],
        "evidence": [
            {
                "id": "ev-1",
                "title": "PaymentGateway definition",
                "source_type": "code",
                "snippet": "class PaymentGateway:\n    pass",
                "path": "app/payments/gateway.py",
            }
        ],
    }

    # Format: Markdown unconstrained
    res_md = TokenBudgetDistiller.distill_brief(
        brief_data=brief_data, token_budget=None, output_format="markdown", registry=registry
    )
    assert res_md.is_distilled is False
    assert res_md.shed_tier == 0
    assert "Pre-Change Investigation Brief" in res_md.content_text
    assert "PaymentGateway definition" in res_md.content_text

    # Format: JSON unconstrained
    res_json = TokenBudgetDistiller.distill_brief(
        brief_data=brief_data, token_budget=None, output_format="json", registry=registry
    )
    assert res_json.is_distilled is False
    assert res_json.content_json["_schema"] == "codeatlas.pre_change_brief.v1"
    assert res_json.content_json["_distilled"] is False
    assert res_json.content_json["targets"]["files"] == ["app/payments/gateway.py"]


def test_pre_change_brief_priority_shedding_under_budget():
    registry = OmissionRegistry()
    # Large brief with many evidence snippets and tests
    brief_data = {
        "summary": "Large investigation report with extensive history",
        "intent_summary": "Major auth module overhaul",
        "target_files": ["app/auth/handler.py", "app/auth/session.py"],
        "target_symbols": ["handle_auth"],
        "claims": [
            {"id": f"cl-{i}", "classification": "fact", "statement": f"Finding {i}"}
            for i in range(10)
        ],
        "signals": {
            "change_risk": {
                "risk_score": 0.85,
                "risk_level": "HIGH",
                "shannon_entropy": 2.4,
                "defect_pressure": 0.9,
                "kamei_metrics": {"lines_added": 400, "lines_deleted": 150, "files_touched": 5},
            },
            "guarding_tests": {
                "untested_files": ["app/auth/session.py"],
                "ranked_tests": [
                    {"test_file": f"tests/test_auth_{i}.py", "reached_target_count": 5 - i}
                    for i in range(8)
                ],
            },
            "blast_radius": {
                "affected_components": ["auth", "api", "middleware"],
                "upstream_callers": [
                    {"path": f"app/routes/api_{i}.py", "depth": i + 1} for i in range(12)
                ],
                "transitive_files": [f"app/routes/api_{i}.py" for i in range(12)],
            },
        },
        "constraints": [
            {
                "id": f"inv-{i}",
                "title": f"Security Constraint {i}",
                "statement": f"Strict session validation rule {i}",
                "level": "must",
                "governing_status": "governing" if i % 2 == 0 else "superseded",
            }
            for i in range(6)
        ],
        "recommended_checks": [f"Verify check {i}" for i in range(8)],
        "evidence": [
            {
                "id": f"ev-{i}",
                "title": f"Evidence {i}",
                "source_type": "commit",
                "snippet": f"commit details and diff analysis for hash abcdef{i}" * 5,
                "path": "app/auth/handler.py",
            }
            for i in range(10)
        ],
    }

    # Distill with strict budget of 400 tokens
    res = TokenBudgetDistiller.distill_brief(
        brief_data=brief_data, token_budget=400, output_format="markdown", registry=registry
    )

    assert res.is_distilled is True
    assert res.shed_tier >= 1
    assert res.omitted_count > 0
    # Check that omission markers were injected in the markdown output
    assert "ref#ev-" in res.content_text
    # Check that high-risk signals are retained (Tier 5 never shed)
    assert "HIGH" in res.content_text
    assert "2.40" in res.content_text  # entropy

    # Also test JSON projection under strict budget
    res_json = TokenBudgetDistiller.distill_brief(
        brief_data=brief_data, token_budget=300, output_format="json", registry=registry
    )
    assert res_json.is_distilled is True
    assert res_json.content_json["_distilled"] is True
    assert res_json.content_json["risk"]["level"] == "HIGH"
    # Ensure evidence refs contain omission markers
    ev_refs = res_json.content_json["evidence_refs"]
    assert any(item.get("_omitted") is True for item in ev_refs)


def test_pre_change_brief_methods():
    brief = PreChangeBrief(
        summary="Investigation summary",
        intent_summary="Intent summary",
        target_files=["backend/app/main.py"],
        target_symbols=["init_app"],
        claims=[
            InvestigationClaim(
                id="c1", classification=ClaimClassification.FACT, statement="Fact statement"
            )
        ],
        signals={"change_risk": {"risk_score": 0.2, "risk_level": "LOW"}},
    )

    md = brief.to_human_markdown(token_budget=500)
    assert "Pre-Change Investigation Brief" in md
    assert "backend/app/main.py" in md

    agent_json = brief.to_agent_json(token_budget=500)
    assert agent_json["_schema"] == "codeatlas.pre_change_brief.v1"
    assert agent_json["targets"]["files"] == ["backend/app/main.py"]


def test_project_context_distillation_and_projections():
    ctx = ProjectContext(
        target_id="repo-1",
        target_name="CodeAtlas",
        target_type="repository",
        summary="A software understanding platform",
        entities=[
            ContextEntity(
                id="e1", name="app/core.py", kind="file", path="app/core.py", language="python"
            ),
            ContextEntity(
                id="e2",
                name="process",
                kind="symbol",
                path="app/core.py",
                line_start=1,
                line_end=20,
            ),
            ContextEntity(
                id="e3", name="app/utils.py", kind="file", path="app/utils.py", language="python"
            ),
        ],
        relationships=[
            ContextRelationship(
                source_name="app/core.py",
                source_path="app/core.py",
                target_name="app/utils.py",
                target_path="app/utils.py",
                type="imports",
            )
        ],
        historical_changes=[
            ContextHistoricalChange(
                commit_hash="c1a2b3c4d5",
                message="Initial commit of core",
                author="Alice",
                committed_at="2026-01-01",
            )
        ],
        design_constraints=[
            ContextDesignConstraint(
                id="dc-1",
                domain="Security",
                priority="MUST",
                constraint_text="Enforce JWT validation",
                source_doc_path="ADR-001.md",
            )
        ],
        evidence=[
            ContextEvidence(
                id="ev-core-1",
                source_path="app/core.py",
                kind="ast_definition",
                content="def process(): pass",
            )
        ],
    )

    # Human markdown unbudgeted
    md_full = ctx.to_human_markdown()
    assert "# Project Context: CodeAtlas" in md_full
    assert "Enforce JWT validation" in md_full

    # Human markdown budgeted
    md_budgeted = ctx.to_human_markdown(token_budget=200)
    assert "# Project Context: CodeAtlas" in md_budgeted

    # Agent JSON
    agent_json = ctx.to_agent_json(token_budget=150)
    assert agent_json["_schema"] == "codeatlas.project_context.v1"
    assert agent_json["target"]["name"] == "CodeAtlas"
    assert "app/core.py" in agent_json["files"]
