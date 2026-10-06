"""Unit & Integration Tests for System One Client & Protocol Adapter."""

from __future__ import annotations

import httpx
import pytest

from app.semantic.client import MockSystemOneClient, SystemOneClient
from app.semantic.systemone import (
    ChoiceAnswer,
    ChoiceQuestion,
    NoulAnswer,
    NoulQuestion,
    ScoreAnswer,
    ScoreQuestion,
    SystemOneRequest,
    SystemOneResponse,
)


def test_systemone_request_serialization():
    """Verify request schema serialization for choice, noul, and score questions."""
    req = SystemOneRequest(
        model="laya-v1",
        state={"file_path": "app/api/endpoints.py", "lines": 42},
        questions={
            "q_arch": ChoiceQuestion(
                instructions="Classify symbol role",
                options=["controller", "service", "repository"],
            ),
            "q_invariant": NoulQuestion(instructions="Is this an architectural invariant?"),
            "q_complexity": ScoreQuestion(
                instructions="Rate complexity",
                legend=["simple", "moderate", "complex"],
            ),
        },
    )

    data = req.model_dump()
    assert data["model"] == "laya-v1"
    assert data["questions"]["q_arch"]["type"] == "choice"
    assert data["questions"]["q_arch"]["options"] == ["controller", "service", "repository"]
    assert data["questions"]["q_invariant"]["type"] == "noul"
    assert data["questions"]["q_complexity"]["type"] == "score"
    assert data["questions"]["q_complexity"]["legend"] == ["simple", "moderate", "complex"]


def test_systemone_response_deserialization():
    """Verify polymorphic answer parsing for response payload."""
    payload = {
        "model": "laya-v1",
        "answers": {
            "q_arch": {
                "type": "choice",
                "choice": "controller",
                "confidence": 0.96,
                "probabilities": {"controller": 0.96, "service": 0.04},
            },
            "q_invariant": {
                "type": "noul",
                "noul": 0.92,
            },
            "q_complexity": {
                "type": "score",
                "score": 0.75,
                "confidence": 0.88,
                "legend": ["simple", "moderate", "complex"],
            },
        },
        "usage": {"input_tokens": 85, "output_tokens": 12},
    }

    res = SystemOneResponse.model_validate(payload)
    assert res.model == "laya-v1"
    assert isinstance(res.answers["q_arch"], ChoiceAnswer)
    assert res.answers["q_arch"].choice == "controller"
    assert res.answers["q_arch"].confidence == 0.96

    assert isinstance(res.answers["q_invariant"], NoulAnswer)
    assert res.answers["q_invariant"].noul == 0.92
    assert res.answers["q_invariant"].certainty == 0.92
    assert res.answers["q_invariant"].boolean_value is True

    assert isinstance(res.answers["q_complexity"], ScoreAnswer)
    assert res.answers["q_complexity"].score == 0.75
    assert res.answers["q_complexity"].confidence == 0.88


@pytest.mark.asyncio
async def test_decide_noul_calibrated_thresholds():
    """Verify noul decision certainty thresholds and fallback behaviour."""
    mock = MockSystemOneClient(confidence_threshold=0.85)

    # 1. High confidence positive (noul = 0.95 -> certainty 0.95 >= 0.85)
    mock.set_noul_response("q_noul", 0.95)
    res = await mock.decide_noul(state="sample", instructions="test", fallback=False)
    assert res.accepted is True
    assert res.value is True
    assert res.confidence == 0.95
    assert res.source == "model"

    # 2. High confidence negative (noul = 0.05 -> certainty 0.95 >= 0.85)
    mock.set_noul_response("q_noul", 0.05)
    res = await mock.decide_noul(state="sample", instructions="test", fallback=True)
    assert res.accepted is True
    assert res.value is False
    assert res.confidence == pytest.approx(0.95)
    assert res.source == "model"

    # 3. Ambiguous confidence (noul = 0.60 -> certainty 0.60 < 0.85) -> triggers fallback
    mock.set_noul_response("q_noul", 0.60)
    res = await mock.decide_noul(state="sample", instructions="test", fallback=False)
    assert res.accepted is False
    assert res.value is False  # Fallback value returned
    assert res.confidence == pytest.approx(0.60)
    assert res.source == "fallback"
    assert "below_threshold" in res.fallback_reason


@pytest.mark.asyncio
async def test_decide_choice_confidence_and_options_validation():
    """Verify choice classification confidence gating and option validation."""
    mock = MockSystemOneClient(confidence_threshold=0.85)

    # 1. High confidence valid choice
    mock.set_choice_response("q_choice", "service", confidence=0.92)
    res = await mock.decide_choice(
        state="class UserService",
        instructions="Pick role",
        options=["controller", "service", "repository"],
        fallback="utility",
    )
    assert res.accepted is True
    assert res.value == "service"
    assert res.confidence == 0.92
    assert res.source == "model"

    # 2. Low confidence choice -> fallback
    mock.set_choice_response("q_choice", "controller", confidence=0.72)
    res = await mock.decide_choice(
        state="ambiguous code",
        instructions="Pick role",
        options=["controller", "service"],
        fallback="utility",
    )
    assert res.accepted is False
    assert res.value == "utility"
    assert res.confidence == 0.72
    assert res.source == "fallback"

    # 3. Choice not in options -> fallback
    mock.set_choice_response("q_choice", "unknown_role", confidence=0.99)
    res = await mock.decide_choice(
        state="class UserService",
        instructions="Pick role",
        options=["controller", "service"],
        fallback="utility",
    )
    assert res.accepted is False
    assert res.value == "utility"
    assert res.source == "fallback"
    assert "not_in_options" in res.fallback_reason


@pytest.mark.asyncio
async def test_decide_score_calibrated_confidence():
    """Verify continuous score evaluation with confidence gating."""
    mock = MockSystemOneClient(confidence_threshold=0.85)

    # 1. High confidence score
    mock.set_score_response("q_score", score=0.82, confidence=0.91)
    res = await mock.decide_score(
        state="code metrics",
        instructions="Score risk",
        legend=["low", "high"],
        fallback=0.1,
    )
    assert res.accepted is True
    assert res.value == 0.82
    assert res.confidence == 0.91
    assert res.source == "model"

    # 2. Low confidence score -> fallback
    mock.set_score_response("q_score", score=0.82, confidence=0.65)
    res = await mock.decide_score(
        state="code metrics",
        instructions="Score risk",
        legend=["low", "high"],
        fallback=0.0,
    )
    assert res.accepted is False
    assert res.value == 0.0
    assert res.confidence == 0.65
    assert res.source == "fallback"


@pytest.mark.asyncio
async def test_evaluate_batch_heterogeneous_questions():
    """Verify batch evaluation of multiple question types in one forward pass."""
    mock = MockSystemOneClient(confidence_threshold=0.85)

    mock.set_choice_response("role", "repository", confidence=0.94)
    mock.set_noul_response("has_side_effects", 0.02)  # High confidence False
    mock.set_score_response("risk_score", 0.35, confidence=0.60)  # Low confidence -> fallback

    questions = {
        "role": ChoiceQuestion(
            instructions="Role",
            options=["service", "repository", "controller"],
        ),
        "has_side_effects": NoulQuestion(instructions="Has side effects?"),
        "risk_score": ScoreQuestion(
            instructions="Risk score",
            legend=["low", "medium", "high"],
        ),
    }
    fallbacks = {
        "role": "utility",
        "has_side_effects": True,
        "risk_score": 0.5,
    }

    results = await mock.evaluate_batch(
        state="class UserRepository: ...",
        questions=questions,
        fallbacks=fallbacks,
    )

    assert len(results) == 3

    assert results["role"].accepted is True
    assert results["role"].value == "repository"
    assert results["role"].source == "model"

    assert results["has_side_effects"].accepted is True
    assert results["has_side_effects"].value is False
    assert results["has_side_effects"].source == "model"

    assert results["risk_score"].accepted is False
    assert results["risk_score"].value == 0.5  # Used fallback
    assert results["risk_score"].source == "fallback"


@pytest.mark.asyncio
async def test_offline_connection_fallback():
    """Verify simulated network disconnect triggers deterministic fallback cleanly."""
    mock = MockSystemOneClient(offline=True)

    res = await mock.decide_noul(
        state="data",
        instructions="Check offline",
        fallback=False,
    )
    assert res.accepted is False
    assert res.value is False
    assert res.source == "fallback"
    assert "ConnectError" in res.fallback_reason


@pytest.mark.asyncio
async def test_client_disabled_configuration():
    """Verify client immediately uses fallback when DECISION_MODEL_ENABLED=False."""
    client = SystemOneClient(enabled=False)

    res = await client.decide_choice(
        state="data",
        instructions="Check disabled",
        options=["a", "b"],
        fallback="default",
    )
    assert res.accepted is False
    assert res.value == "default"
    assert res.fallback_reason == "client_disabled"


@pytest.mark.asyncio
async def test_http_mock_transport_integration():
    """Verify SystemOneClient over httpx MockTransport with wire HTTP payload."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/systemone"
        import json

        data = json.loads(request.content)
        assert data["model"] == "laya-latest"
        assert "q1" in data["questions"]

        return httpx.Response(
            200,
            json={
                "model": "laya-latest",
                "answers": {
                    "q1": {
                        "type": "choice",
                        "choice": "controller",
                        "confidence": 0.98,
                        "probabilities": {"controller": 0.98, "service": 0.02},
                    }
                },
            },
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = SystemOneClient(
            base_url="http://mock-server:8081",
            http_client=http_client,
            confidence_threshold=0.85,
        )

        res = await client.decide_choice(
            state="def get_users(): ...",
            instructions="Pick role",
            options=["controller", "service"],
            fallback="utility",
            question_id="q1",
        )
        assert res.accepted is True
        assert res.value == "controller"
        assert res.confidence == 0.98
        assert res.source == "model"
