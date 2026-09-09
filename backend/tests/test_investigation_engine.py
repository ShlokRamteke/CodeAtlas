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
        file_commits=[
            {
                "hash": "abc12345",
                "message": "Add PaymentHandler initial implementation",
                "author": "dev@codeatlas.dev",
            }
        ],
    )

    assert state.step == InvestigationStep.COMPLETED
    assert state.brief is not None
    assert len(state.claims) > 0
    assert len(state.gathered_evidence) >= 2
    assert state.model_calls_count <= 3
    assert state.latency_ms >= 0

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
