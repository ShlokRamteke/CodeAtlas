from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.investigation.intent import IntentNormalizer, NormalizedChangeIntent
from app.investigation.llm import MockLLMProvider
from app.investigation.planner import InvestigationEngine
from app.investigation.state import (
    InvestigationPlan,
    InvestigationState,
    InvestigationStep,
)
from app.models.investigation import Investigation, InvestigationStatus
from app.models.repository import Repository


def test_intent_normalizer_explicit_and_heuristics():
    query = "Refactor StripePaymentGateway in backend/app/payments/stripe.py and replace checkout_session"
    intent = IntentNormalizer.normalize(
        raw_query=query,
        known_files=["backend/app/payments/stripe.py", "backend/app/main.py"],
    )

    assert "refactor" in intent.action_verbs or "replace" in intent.action_verbs
    assert "backend/app/payments/stripe.py" in intent.target_files
    assert "StripePaymentGateway" in intent.target_symbols
    assert "checkout_session" in intent.target_symbols
    assert "payments" in intent.target_components or "backend" in intent.target_components
    assert intent.is_ambiguous is False


def test_intent_normalizer_ambiguous():
    query = "make it better"
    intent = IntentNormalizer.normalize(raw_query=query)
    assert intent.is_ambiguous is True
    assert len(intent.target_files) == 0
    assert len(intent.target_symbols) == 0


def test_bounded_model_call_enforcement():
    state = InvestigationState(
        investigation_id=uuid.uuid4(),
        repository_id=uuid.uuid4(),
        query="Replace payment system",
        max_model_calls=3,
    )

    assert state.can_call_model is True
    state.record_model_call(prompt_tokens=100, completion_tokens=50)
    assert state.model_calls_count == 1
    assert state.token_usage["total_tokens"] == 150

    state.record_model_call(prompt_tokens=100, completion_tokens=50)
    assert state.model_calls_count == 2
    assert state.can_call_model is True

    state.record_model_call(prompt_tokens=100, completion_tokens=50)
    assert state.model_calls_count == 3
    assert state.can_call_model is False

    # Exceeding budget raises RuntimeError
    with pytest.raises(RuntimeError, match="Bounded investigation limit exceeded"):
        state.record_model_call(prompt_tokens=10, completion_tokens=10)


@pytest.mark.asyncio
async def test_mock_llm_provider_flow():
    provider = MockLLMProvider()
    intent = NormalizedChangeIntent(
        raw_query="Migrate auth session token",
        action_verbs=["migrate"],
        target_files=["app/auth/session.py"],
        target_symbols=["SessionManager"],
    )

    plan, tokens = await provider.plan_investigation(intent, "preview")
    assert isinstance(plan, InvestigationPlan)
    assert tokens["prompt_tokens"] > 0

    summary, claims, tokens = await provider.reason_investigation(intent, "context", {})
    assert len(claims) == 3
    assert tokens["completion_tokens"] > 0

    # Verification checks evidence citations
    evidence_catalog = [{"id": "ev-1", "source_id": "app/auth/session.py"}]
    verified_claims, _ = await provider.verify_claims(claims, evidence_catalog)
    assert len(verified_claims) == 3
    # First claim had ev-1, should retain confidence 1.0
    assert verified_claims[0].confidence == 1.0


@pytest.mark.asyncio
async def test_investigation_engine_end_to_end(db_session: AsyncSession):
    # Setup repo and investigation
    repo = Repository(
        owner="archaeologist",
        name="test-repo",
        full_name="archaeologist/test-repo",
        default_branch="main",
    )
    db_session.add(repo)
    await db_session.commit()
    await db_session.refresh(repo)

    inv = Investigation(
        repository_id=repo.id,
        query="Refactor PaymentHandler in payments/gateway.py",
    )
    db_session.add(inv)
    await db_session.commit()
    await db_session.refresh(inv)

    # Add SourceFile and CodeDependency
    from datetime import datetime, timezone

    from app.models.commit import Commit
    from app.models.commit_file_change import ChangeType, CommitFileChange
    from app.models.dependency import CodeDependency
    from app.models.source_file import SourceFile

    src_file = SourceFile(
        repository_id=repo.id,
        path="payments/gateway.py",
        language="python",
        content_hash="h1",
        size_bytes=100,
    )
    caller_file = SourceFile(
        repository_id=repo.id,
        path="orders/service.py",
        language="python",
        content_hash="h2",
        size_bytes=100,
    )

    db_session.add_all([src_file, caller_file])
    await db_session.commit()
    await db_session.refresh(src_file)
    await db_session.refresh(caller_file)

    dep = CodeDependency(
        repository_id=repo.id,
        source_file_id=caller_file.id,
        source_path="orders/service.py",
        target_path="payments/gateway.py",
    )
    db_session.add(dep)

    # Add historical commits with co-changes: gateway.py & config/payments.yaml
    c1 = Commit(
        repository_id=repo.id,
        commit_hash="c111111111111111111111111111111111111111",
        author_name="dev",
        author_email="dev@example.com",
        committed_at=datetime.now(timezone.utc),
        message="feat: payment gateway and config",
    )
    c2 = Commit(
        repository_id=repo.id,
        commit_hash="c222222222222222222222222222222222222222",
        author_name="dev",
        author_email="dev@example.com",
        committed_at=datetime.now(timezone.utc),
        message="fix: payment retry and config",
    )
    db_session.add_all([c1, c2])
    await db_session.commit()
    await db_session.refresh(c1)
    await db_session.refresh(c2)

    fc1 = CommitFileChange(
        commit_id=c1.id, file_path="payments/gateway.py", change_type=ChangeType.MODIFIED
    )
    fc2 = CommitFileChange(
        commit_id=c1.id, file_path="config/payments.yaml", change_type=ChangeType.MODIFIED
    )
    fc3 = CommitFileChange(
        commit_id=c2.id, file_path="payments/gateway.py", change_type=ChangeType.MODIFIED
    )
    fc4 = CommitFileChange(
        commit_id=c2.id, file_path="config/payments.yaml", change_type=ChangeType.MODIFIED
    )
    db_session.add_all([fc1, fc2, fc3, fc4])
    await db_session.commit()

    mock_llm = MockLLMProvider()
    engine = InvestigationEngine(llm_provider=mock_llm)

    state = await engine.run(
        investigation_id=inv.id,
        db=db_session,
        target_path="payments/gateway.py",
        target_symbol="PaymentHandler",
        code_snippets=[
            {
                "path": "payments/gateway.py",
                "code": "class PaymentHandler:\n    def process(): pass",
                "line_start": 1,
                "line_end": 2,
            }
        ],
    )

    assert state.step == InvestigationStep.COMPLETED
    assert state.brief is not None
    assert len(state.claims) > 0
    assert len(state.gathered_evidence) >= 2
    assert state.model_calls_count <= 3
    assert state.latency_ms >= 0

    # Verify blast radius signal
    assert "blast_radius" in state.gathered_signals
    blast_sig = state.gathered_signals["blast_radius"]
    assert "orders/service.py" in [n["path"] for n in blast_sig["upstream_callers"]]
    assert "orders" in blast_sig["affected_components"]

    # Verify co-change signal & hidden coupling warning
    assert "co_change" in state.gathered_signals
    co_sig = state.gathered_signals["co_change"]
    assert co_sig["has_hidden_coupling"] is True
    omitted = [w["omitted_partner"] for w in co_sig["hidden_coupling_warnings"]]
    assert "config/payments.yaml" in omitted

    # Verify recommendations & unknowns captured in brief
    assert any("config/payments.yaml" in r for r in state.brief.recommended_checks)
    assert any("config/payments.yaml" in u for u in state.brief.unknowns)

    # Verify persisted DB entity
    await db_session.refresh(inv, attribute_names=["evidence"])
    assert inv.status == InvestigationStatus.COMPLETED
    assert inv.summary is not None
    assert len(inv.claims) > 0
    assert len(inv.evidence) >= 2


@pytest.mark.asyncio
async def test_investigation_api_preview_and_run(client: AsyncClient):
    repo_payload = {
        "owner": "testorg",
        "name": "apirepo",
        "full_name": "testorg/apirepo",
        "default_branch": "main",
    }
    repo_res = await client.post("/api/v1/repositories/", json=repo_payload)
    assert repo_res.status_code == 201
    repo_id = repo_res.json()["id"]

    # Preview intent endpoint
    preview_res = await client.post(
        "/api/v1/investigations/preview-intent",
        params={
            "query": "Upgrade AuthProvider in backend/auth/provider.py",
            "target_path": "backend/auth/provider.py",
        },
    )
    assert preview_res.status_code == 200
    intent_data = preview_res.json()
    assert "upgrade" in intent_data["action_verbs"]
    assert "backend/auth/provider.py" in intent_data["target_files"]

    # Create investigation
    inv_res = await client.post(
        "/api/v1/investigations/",
        json={
            "repository_id": repo_id,
            "query": "Upgrade AuthProvider in backend/auth/provider.py",
            "type": "before_change",
            "target_path": "backend/auth/provider.py",
            "target_symbol": "AuthProvider",
        },
    )
    assert inv_res.status_code == 201
    inv_id = inv_res.json()["id"]

    # Run investigation endpoint
    run_res = await client.post(
        f"/api/v1/investigations/{inv_id}/run",
        json={"target_path": "backend/auth/provider.py", "target_symbol": "AuthProvider"},
    )
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert run_data["status"] == "completed"
    assert run_data["summary"] is not None
    assert len(run_data["claims"]) > 0
    assert len(run_data["evidence"]) > 0


def test_openrouter_provider_configuration():
    from app.investigation.llm import OpenRouterLLMProvider, get_default_llm_provider

    provider = OpenRouterLLMProvider(
        api_key="test-or-key",
        model="anthropic/claude-3.5-sonnet",
        base_url="https://openrouter.ai/api/v1",
    )
    assert provider.api_key == "test-or-key"
    assert provider.model == "anthropic/claude-3.5-sonnet"
    assert provider.headers["Authorization"] == "Bearer test-or-key"
    assert provider.headers["HTTP-Referer"] == "https://codeatlas.dev"
    assert provider.headers["X-Title"] == "CodeAtlas"

    default_provider = get_default_llm_provider()
    assert default_provider is not None


@pytest.mark.asyncio
async def test_investigation_engine_with_diff_input(db_session: AsyncSession):
    repo = Repository(
        owner="testorg",
        name="riskengine",
        full_name="testorg/riskengine",
        default_branch="main",
    )
    db_session.add(repo)
    await db_session.commit()
    await db_session.refresh(repo)

    inv = Investigation(
        repository_id=repo.id,
        query="Refactor database schema across auth and billing",
    )
    db_session.add(inv)
    await db_session.commit()
    await db_session.refresh(inv)

    sample_diff = """diff --git a/backend/app/auth/service.py b/backend/app/auth/service.py
index 0000000..1111111 100644
--- a/backend/app/auth/service.py
+++ b/backend/app/auth/service.py
@@ -1,5 +1,15 @@
+import hashlib
+def hash_token(): pass
+def verify_token(): pass
-def old_auth(): pass
diff --git a/backend/app/billing/charge.py b/backend/app/billing/charge.py
--- a/backend/app/billing/charge.py
+++ b/backend/app/billing/charge.py
@@ -10,3 +10,12 @@
+def process_charge(): pass
+def refund(): pass
"""

    mock_llm = MockLLMProvider()
    engine = InvestigationEngine(llm_provider=mock_llm)

    state = await engine.run(
        investigation_id=inv.id,
        db=db_session,
        diff=sample_diff,
    )

    assert state.step == InvestigationStep.COMPLETED
    assert "change_risk" in state.gathered_signals

    risk_sig = state.gathered_signals["change_risk"]
    assert risk_sig["lines_added"] == 5
    assert risk_sig["lines_deleted"] == 1
    assert risk_sig["file_count"] == 2
    assert risk_sig["shannon_entropy"] > 0.0
    assert risk_sig["risk_score"] >= 0.0
    assert risk_sig["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")

    # Check evidence records
    risk_ev = next(
        (ev for ev in state.gathered_evidence if ev.get("source_id") == "kamei-change-risk"),
        None,
    )
    assert risk_ev is not None
    assert "Quantitative Change Risk" in risk_ev["title"]
    assert risk_ev["extra_metadata"]["kamei_metrics"]["lines_added"] == 5
    assert risk_ev["extra_metadata"]["kamei_metrics"]["lines_deleted"] == 1


@pytest.mark.asyncio
async def test_investigation_engine_guarding_tests_reach_ranking(db_session: AsyncSession):
    from app.models.dependency import CodeDependency
    from app.models.source_file import SourceFile

    repo = Repository(
        owner="testorg",
        name="testranking",
        full_name="testorg/testranking",
        default_branch="main",
    )
    db_session.add(repo)
    await db_session.commit()
    await db_session.refresh(repo)

    # Add source files
    sf1 = SourceFile(
        repository_id=repo.id,
        path="backend/app/auth/service.py",
        language="python",
        content_hash="h1",
    )
    sf2 = SourceFile(
        repository_id=repo.id,
        path="backend/app/billing/charge.py",
        language="python",
        content_hash="h2",
    )
    sf3 = SourceFile(
        repository_id=repo.id,
        path="tests/test_auth.py",
        language="python",
        content_hash="h3",
    )
    sf4 = SourceFile(
        repository_id=repo.id,
        path="tests/test_integration.py",
        language="python",
        content_hash="h4",
    )
    db_session.add_all([sf1, sf2, sf3, sf4])
    await db_session.commit()
    await db_session.refresh(sf1)
    await db_session.refresh(sf2)
    await db_session.refresh(sf3)
    await db_session.refresh(sf4)

    # Add test dependencies
    # test_integration guards BOTH auth and billing
    dep1 = CodeDependency(
        repository_id=repo.id,
        source_file_id=sf4.id,
        source_path="tests/test_integration.py",
        target_path="backend/app/auth/service.py",
    )
    dep2 = CodeDependency(
        repository_id=repo.id,
        source_file_id=sf4.id,
        source_path="tests/test_integration.py",
        target_path="backend/app/billing/charge.py",
    )
    # test_auth guards only auth
    dep3 = CodeDependency(
        repository_id=repo.id,
        source_file_id=sf3.id,
        source_path="tests/test_auth.py",
        target_path="backend/app/auth/service.py",
    )
    db_session.add_all([dep1, dep2, dep3])
    await db_session.commit()

    inv = Investigation(
        repository_id=repo.id,
        query="Refactor auth and billing",
    )
    db_session.add(inv)
    await db_session.commit()
    await db_session.refresh(inv)

    diff_content = """diff --git a/backend/app/auth/service.py b/backend/app/auth/service.py
--- a/backend/app/auth/service.py
+++ b/backend/app/auth/service.py
@@ -1,2 +1,3 @@
+def new_auth(): pass
diff --git a/backend/app/billing/charge.py b/backend/app/billing/charge.py
--- a/backend/app/billing/charge.py
+++ b/backend/app/billing/charge.py
@@ -1,2 +1,3 @@
+def new_charge(): pass
"""

    engine = InvestigationEngine(llm_provider=MockLLMProvider())
    state = await engine.run(
        investigation_id=inv.id,
        db=db_session,
        diff=diff_content,
    )

    assert state.step == InvestigationStep.COMPLETED
    assert "guarding_tests" in state.gathered_signals
    gt_sig = state.gathered_signals["guarding_tests"]

    assert gt_sig["total_guarding_tests"] == 2
    # Reach ranking: test_integration guards 2 targets, test_auth guards 1
    assert gt_sig["ranked_tests"][0]["test_file"] == "tests/test_integration.py"
    assert gt_sig["ranked_tests"][0]["reached_target_count"] == 2
    assert gt_sig["ranked_tests"][1]["test_file"] == "tests/test_auth.py"
    assert gt_sig["ranked_tests"][1]["reached_target_count"] == 1

    # Check evidence record
    gt_ev = next(
        (ev for ev in state.gathered_evidence if ev.get("source_id") == "guarding-tests"),
        None,
    )
    assert gt_ev is not None
    assert "Guarding Tests" in gt_ev["title"]
    assert "tests/test_integration.py" in gt_ev["snippet"]

    # Check recommendations
    assert any("test_integration.py" in r for r in state.brief.recommended_checks)
