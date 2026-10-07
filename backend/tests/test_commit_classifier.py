"""Unit Tests for Git Commit Intent & Defect Fix Classifier."""

from __future__ import annotations

import pytest

from app.semantic.client import MockSystemOneClient
from app.semantic.commit_classifier import (
    CommitIntent,
    CommitIntentClassifier,
)


def test_heuristic_classify_conventional_commits():
    """Verify standard conventional commit prefixes map to correct intents."""
    # Feat
    intent, is_defect = CommitIntentClassifier.heuristic_classify(
        "feat(auth): implement oauth2 login with github"
    )
    assert intent == CommitIntent.FEATURE
    assert is_defect is False

    # Fix
    intent, is_defect = CommitIntentClassifier.heuristic_classify(
        "fix(api): resolve null pointer exception when body is empty"
    )
    assert intent == CommitIntent.BUGFIX
    assert is_defect is True

    # Hotfix
    intent, is_defect = CommitIntentClassifier.heuristic_classify(
        "hotfix: prevent database connection pool exhaustion"
    )
    assert intent == CommitIntent.BUGFIX
    assert is_defect is True

    # Refactor
    intent, is_defect = CommitIntentClassifier.heuristic_classify(
        "refactor(engine): decouple tree-sitter parser from indexer"
    )
    assert intent == CommitIntent.REFACTOR
    assert is_defect is False

    # Security
    intent, is_defect = CommitIntentClassifier.heuristic_classify(
        "sec(crypto): rotate signing keys and patch timing leak"
    )
    assert intent == CommitIntent.SECURITY_PATCH
    assert is_defect is True

    # Chore
    intent, is_defect = CommitIntentClassifier.heuristic_classify(
        "chore(deps): bump pydantic from 2.8.0 to 2.9.0"
    )
    assert intent == CommitIntent.CHORE
    assert is_defect is False

    # Docs / Tests
    intent, is_defect = CommitIntentClassifier.heuristic_classify(
        "test: add unit tests for defect pressure mining"
    )
    assert intent == CommitIntent.CHORE
    assert is_defect is False


def test_heuristic_classify_natural_language_messages():
    """Verify non-conventional commit messages map correctly via semantic keywords."""
    # Defect / Bug fix
    intent, is_defect = CommitIntentClassifier.heuristic_classify(
        "repair race condition in background cache worker"
    )
    assert intent == CommitIntent.BUGFIX
    assert is_defect is True

    intent, is_defect = CommitIntentClassifier.heuristic_classify(
        "patch memory leak on websocket disconnect, closes #42"
    )
    assert intent == CommitIntent.BUGFIX
    assert is_defect is True

    # Security vulnerability
    intent, is_defect = CommitIntentClassifier.heuristic_classify(
        "mitigate CVE-2025-9981 sql injection vulnerability in query filter"
    )
    assert intent == CommitIntent.SECURITY_PATCH
    assert is_defect is True

    intent, is_defect = CommitIntentClassifier.heuristic_classify(
        "prevent cross-site scripting xss vulnerability in markdown renderer"
    )
    assert intent == CommitIntent.SECURITY_PATCH
    assert is_defect is True

    # Feature
    intent, is_defect = CommitIntentClassifier.heuristic_classify(
        "add new export format for mermaid diagrams and C4 architecture"
    )
    assert intent == CommitIntent.FEATURE
    assert is_defect is False

    # Refactor
    intent, is_defect = CommitIntentClassifier.heuristic_classify(
        "simplify component tree and consolidate duplicate handlers"
    )
    assert intent == CommitIntent.REFACTOR
    assert is_defect is False

    # Chore by touched files
    intent, is_defect = CommitIntentClassifier.heuristic_classify(
        "update project information",
        touched_files=["README.md", "docs/overview.md"],
    )
    assert intent == CommitIntent.CHORE
    assert is_defect is False


@pytest.mark.asyncio
async def test_commit_classifier_model_acceptance():
    """Verify that model predictions with confidence >= 0.85 are accepted."""
    mock_client = MockSystemOneClient(confidence_threshold=0.85)
    mock_client.set_choice_response("intent_c1", "feature", confidence=0.92)
    mock_client.set_noul_response("defect_c1", 0.05)

    classifier = CommitIntentClassifier(client=mock_client)
    res = await classifier.classify_commit(
        message="introduce payment retry queue",
        commit_hash="c1",
        touched_files=["src/queue.py"],
    )

    assert res.commit_intent == CommitIntent.FEATURE
    assert res.is_defect_fix is False
    assert res.source == "model"
    assert res.intent_confidence == 0.92
    assert res.defect_confidence == 0.95


@pytest.mark.asyncio
async def test_commit_classifier_defect_acceptance():
    """Verify that model defect classification with confidence >= 0.85 is accepted."""
    mock_client = MockSystemOneClient(confidence_threshold=0.85)
    mock_client.set_choice_response("intent_c2", "bugfix", confidence=0.94)
    mock_client.set_noul_response("defect_c2", 0.96)

    classifier = CommitIntentClassifier(client=mock_client)
    res = await classifier.classify_commit(
        message="resolve thread deadlock in worker loop",
        commit_hash="c2",
        touched_files=["src/worker.py"],
    )

    assert res.commit_intent == CommitIntent.BUGFIX
    assert res.is_defect_fix is True
    assert res.source == "model"


@pytest.mark.asyncio
async def test_commit_classifier_low_confidence_fallback():
    """Verify that predictions with confidence < 0.85 fall back to deterministic heuristics."""
    mock_client = MockSystemOneClient(confidence_threshold=0.85)
    mock_client.set_choice_response("intent_c3", "chore", confidence=0.60)
    mock_client.set_noul_response("defect_c3", 0.50)

    classifier = CommitIntentClassifier(client=mock_client)
    # Message is clearly a bugfix conventionally
    res = await classifier.classify_commit(
        message="fix(auth): fix crash on invalid jwt token",
        commit_hash="c3",
        touched_files=["src/auth.py"],
    )

    # Low confidence rejected -> falls back to heuristic BUGFIX / True
    assert res.commit_intent == CommitIntent.BUGFIX
    assert res.is_defect_fix is True
    assert res.source == "heuristic"
    assert "below_threshold" in (res.fallback_reason or "")


@pytest.mark.asyncio
async def test_commit_classifier_disabled_fallback():
    """Verify that disabled decision client falls back immediately without errors."""
    mock_client = MockSystemOneClient(enabled=False)
    classifier = CommitIntentClassifier(client=mock_client)

    res = await classifier.classify_commit(
        message="feat: add telemetry metrics endpoint",
        commit_hash="c4",
    )

    assert res.commit_intent == CommitIntent.FEATURE
    assert res.is_defect_fix is False
    assert res.source == "heuristic"


@pytest.mark.asyncio
async def test_commit_classifier_batch_evaluation():
    """Verify batch classification across multiple commits in a single pass."""
    mock_client = MockSystemOneClient(confidence_threshold=0.85)
    mock_client.set_choice_response("intent_h1", "feature", confidence=0.90)
    mock_client.set_noul_response("defect_h1", 0.05)

    mock_client.set_choice_response("intent_h2", "bugfix", confidence=0.95)
    mock_client.set_noul_response("defect_h2", 0.98)

    mock_client.set_choice_response("intent_h3", "security_patch", confidence=0.91)
    mock_client.set_noul_response("defect_h3", 0.95)

    classifier = CommitIntentClassifier(client=mock_client)

    commits = [
        {
            "commit_hash": "h1",
            "message": "feat: user notifications",
            "touched_files": ["app/notify.py"],
        },
        {
            "commit_hash": "h2",
            "message": "fix: race in notify worker",
            "touched_files": ["app/worker.py"],
        },
        {
            "commit_hash": "h3",
            "message": "sec: patch CVE in auth",
            "touched_files": ["app/auth.py"],
        },
    ]

    batch_res = await classifier.classify_commits_batch(commits)

    assert len(batch_res) == 3
    assert batch_res["h1"].commit_intent == CommitIntent.FEATURE
    assert batch_res["h1"].is_defect_fix is False

    assert batch_res["h2"].commit_intent == CommitIntent.BUGFIX
    assert batch_res["h2"].is_defect_fix is True

    assert batch_res["h3"].commit_intent == CommitIntent.SECURITY_PATCH
    assert batch_res["h3"].is_defect_fix is True


@pytest.mark.asyncio
async def test_commit_classifier_harmonization():
    """Verify that when intent is bugfix/security_patch, is_defect_fix is True regardless of raw noul."""
    mock_client = MockSystemOneClient(confidence_threshold=0.85)
    mock_client.set_choice_response("intent_h4", "bugfix", confidence=0.92)
    # Model noul returned false/low, but intent is explicitly bugfix
    mock_client.set_noul_response("defect_h4", 0.30)

    classifier = CommitIntentClassifier(client=mock_client)
    res = await classifier.classify_commit(
        message="resolve edge case null check",
        commit_hash="h4",
    )

    assert res.commit_intent == CommitIntent.BUGFIX
    assert res.is_defect_fix is True
