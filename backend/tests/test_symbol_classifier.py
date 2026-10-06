"""Unit Tests for Architectural Symbol Role Classifier."""

from __future__ import annotations

import pytest

from app.models.symbol import ArchitecturalRole
from app.parser.ast_parser import ExtractedSymbol
from app.semantic.client import MockSystemOneClient
from app.semantic.symbol_classifier import SymbolRoleClassifier


def test_heuristic_classify_controller():
    """Verify controller detection from path, naming, and decorators."""
    # By path
    role = SymbolRoleClassifier.heuristic_classify(
        name="get_users",
        file_path="app/api/v1/endpoints/users.py",
        kind="function",
    )
    assert role == ArchitecturalRole.CONTROLLER

    # By naming
    role = SymbolRoleClassifier.heuristic_classify(
        name="PaymentController",
        file_path="src/payments.ts",
        kind="class",
    )
    assert role == ArchitecturalRole.CONTROLLER

    # By decorator
    role = SymbolRoleClassifier.heuristic_classify(
        name="handle_request",
        file_path="src/handler.py",
        kind="function",
        decorators=["@router.get('/items')"],
    )
    assert role == ArchitecturalRole.CONTROLLER


def test_heuristic_classify_repository():
    """Verify repository detection from path, naming, and query methods."""
    # By path
    role = SymbolRoleClassifier.heuristic_classify(
        name="UserStore",
        file_path="app/repositories/user_repository.py",
        kind="class",
    )
    assert role == ArchitecturalRole.REPOSITORY

    # By naming
    role = SymbolRoleClassifier.heuristic_classify(
        name="OrderRepository",
        file_path="src/orders.ts",
        kind="class",
    )
    assert role == ArchitecturalRole.REPOSITORY

    # By query methods
    role = SymbolRoleClassifier.heuristic_classify(
        name="DataStore",
        file_path="src/store.py",
        kind="class",
        method_names=["find_by_id", "save", "delete_by_key"],
    )
    assert role == ArchitecturalRole.REPOSITORY


def test_heuristic_classify_service():
    """Verify service detection from path, naming, and business keywords."""
    # By path
    role = SymbolRoleClassifier.heuristic_classify(
        name="Authenticator",
        file_path="app/services/auth.py",
        kind="class",
    )
    assert role == ArchitecturalRole.SERVICE

    # By naming
    role = SymbolRoleClassifier.heuristic_classify(
        name="CheckoutService",
        file_path="src/checkout.ts",
        kind="class",
    )
    assert role == ArchitecturalRole.SERVICE

    # By docstring
    role = SymbolRoleClassifier.heuristic_classify(
        name="BillingEngine",
        file_path="src/billing.py",
        kind="class",
        docstring="Core service for processing customer billing schedules.",
    )
    assert role == ArchitecturalRole.SERVICE


def test_heuristic_classify_entity():
    """Verify entity detection from models, schemas, and dataclasses."""
    # By path
    role = SymbolRoleClassifier.heuristic_classify(
        name="UserProfile",
        file_path="app/models/user.py",
        kind="class",
    )
    assert role == ArchitecturalRole.ENTITY

    # By naming
    role = SymbolRoleClassifier.heuristic_classify(
        name="TransactionDTO",
        file_path="src/types.ts",
        kind="interface",
    )
    assert role == ArchitecturalRole.ENTITY

    # By decorator
    role = SymbolRoleClassifier.heuristic_classify(
        name="CustomerRecord",
        file_path="src/customer.py",
        kind="class",
        decorators=["@dataclass"],
    )
    assert role == ArchitecturalRole.ENTITY


def test_heuristic_classify_middleware():
    """Verify middleware detection from path and naming."""
    # By path
    role = SymbolRoleClassifier.heuristic_classify(
        name="jwt_guard",
        file_path="app/middleware/jwt.py",
        kind="function",
    )
    assert role == ArchitecturalRole.MIDDLEWARE

    # By naming
    role = SymbolRoleClassifier.heuristic_classify(
        name="CorsMiddleware",
        file_path="src/server.ts",
        kind="class",
    )
    assert role == ArchitecturalRole.MIDDLEWARE


def test_heuristic_classify_utility():
    """Verify utility detection from helpers, common paths, and utility naming."""
    # By path
    role = SymbolRoleClassifier.heuristic_classify(
        name="format_date",
        file_path="app/utils/date.py",
        kind="function",
    )
    assert role == ArchitecturalRole.UTILITY

    # By naming
    role = SymbolRoleClassifier.heuristic_classify(
        name="StringFormatter",
        file_path="src/text.ts",
        kind="class",
    )
    assert role == ArchitecturalRole.UTILITY


@pytest.mark.asyncio
async def test_symbol_classifier_model_acceptance():
    """Verify that model predictions with confidence >= 0.85 are accepted."""
    mock_client = MockSystemOneClient(confidence_threshold=0.85)
    mock_client.set_choice_response("architectural_role", "repository", confidence=0.92)

    classifier = SymbolRoleClassifier(client=mock_client)
    symbol = ExtractedSymbol(
        name="CustomStore",
        kind="class",
        line_start=10,
        line_end=40,
        signature="class CustomStore:",
    )

    result = await classifier.classify_symbol(symbol, "src/storage.py")
    assert result.accepted is True
    assert result.value == ArchitecturalRole.REPOSITORY
    assert result.confidence == 0.92
    assert result.source == "model"


@pytest.mark.asyncio
async def test_symbol_classifier_low_confidence_fallback():
    """Verify that model predictions with confidence < 0.85 fall back to deterministic heuristic."""
    mock_client = MockSystemOneClient(confidence_threshold=0.85)
    mock_client.set_choice_response("architectural_role", "utility", confidence=0.65)

    classifier = SymbolRoleClassifier(client=mock_client)
    symbol = ExtractedSymbol(
        name="get_accounts",
        kind="function",
        line_start=5,
        line_end=20,
        decorators=["@router.get('/accounts')"],
    )

    result = await classifier.classify_symbol(symbol, "app/api/endpoints/accounts.py")
    assert result.accepted is False
    # Heuristic classifies as controller due to /api/ endpoints and @router.get
    assert result.value == ArchitecturalRole.CONTROLLER
    assert result.source == "fallback"
    assert "below_threshold" in (result.fallback_reason or "")


@pytest.mark.asyncio
async def test_symbol_classifier_disabled_fallback():
    """Verify that disabled decision client falls back immediately without network requests."""
    mock_client = MockSystemOneClient(enabled=False)
    classifier = SymbolRoleClassifier(client=mock_client)

    symbol = ExtractedSymbol(
        name="OrderService",
        kind="class",
        line_start=1,
        line_end=50,
    )
    result = await classifier.classify_symbol(symbol, "app/services/orders.py")
    assert result.accepted is False
    assert result.value == ArchitecturalRole.SERVICE
    assert result.source == "fallback"
    assert result.fallback_reason == "client_disabled"


@pytest.mark.asyncio
async def test_symbol_classifier_batch():
    """Verify batch classification of multiple symbols in a file."""
    mock_client = MockSystemOneClient(confidence_threshold=0.85)
    mock_client.set_choice_response("q_0_AuthService", "service", confidence=0.95)
    mock_client.set_choice_response("q_1_UserToken", "entity", confidence=0.90)

    classifier = SymbolRoleClassifier(client=mock_client)
    symbols = [
        ExtractedSymbol(
            name="AuthService",
            kind="class",
            line_start=1,
            line_end=30,
        ),
        ExtractedSymbol(
            name="UserToken",
            kind="class",
            line_start=32,
            line_end=45,
            decorators=["@dataclass"],
        ),
    ]

    results = await classifier.classify_symbols_batch(symbols, "app/auth/service.py")
    assert len(results) == 2
    assert results["q_0_AuthService"].accepted is True
    assert results["q_0_AuthService"].value == ArchitecturalRole.SERVICE
    assert results["q_1_UserToken"].accepted is True
    assert results["q_1_UserToken"].value == ArchitecturalRole.ENTITY
