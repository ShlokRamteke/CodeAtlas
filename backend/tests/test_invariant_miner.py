"""Unit & Integration Tests for Semantic Invariant Miner."""

from __future__ import annotations

import pytest

from app.parser.doc_parser import (
    EngineeringContextParser,
    ParsedConstraint,
    ParsedConstraintCategory,
    ParsedConstraintLevel,
)
from app.semantic.client import MockSystemOneClient
from app.semantic.invariant_miner import SemanticInvariantMiner
from app.semantic.systemone import NoulAnswer


def test_heuristic_classify_security():
    """Verify heuristic invariant detection for security policies."""
    # Positive: sanitize user input
    is_inv, cat, lvl, domain = SemanticInvariantMiner.heuristic_classify(
        "Sanitize all user-supplied parameters before executing database queries."
    )
    assert is_inv is True
    assert cat == ParsedConstraintCategory.SECURITY
    assert lvl == ParsedConstraintLevel.MUST
    assert domain == "security"

    # Positive: prohibit secret storage
    is_inv, cat, lvl, domain = SemanticInvariantMiner.heuristic_classify(
        "Do not store plaintext passwords or authentication tokens in session storage."
    )
    assert is_inv is True
    assert cat == ParsedConstraintCategory.SECURITY
    assert lvl == ParsedConstraintLevel.MUST_NOT
    assert domain == "security"


def test_heuristic_classify_concurrency_and_performance():
    """Verify concurrency (mapped to performance) and latency rules."""
    # Concurrency rule
    is_inv, cat, lvl, domain = SemanticInvariantMiner.heuristic_classify(
        "All concurrent database connections must acquire locks in ascending order to prevent deadlocks."
    )
    assert is_inv is True
    assert cat == ParsedConstraintCategory.PERFORMANCE
    assert lvl == ParsedConstraintLevel.MUST_NOT or lvl == ParsedConstraintLevel.MUST
    assert domain == "concurrency"

    # Latency recommendation
    is_inv, cat, lvl, domain = SemanticInvariantMiner.heuristic_classify(
        "API response latencies should remain under 200ms at p99."
    )
    assert is_inv is True
    assert cat == ParsedConstraintCategory.PERFORMANCE
    assert lvl == ParsedConstraintLevel.SHOULD
    assert domain == "performance"


def test_heuristic_classify_data_integrity():
    """Verify transactional and consistency invariants."""
    is_inv, cat, lvl, domain = SemanticInvariantMiner.heuristic_classify(
        "All state-changing operations require transactional rollbacks upon failure."
    )
    assert is_inv is True
    assert cat == ParsedConstraintCategory.DATA_INTEGRITY
    assert lvl == ParsedConstraintLevel.MUST
    assert domain == "data_integrity"


def test_heuristic_classify_deployment_and_architecture():
    """Verify deployment (mapped to architecture) and structural invariants."""
    # Deployment constraint
    is_inv, cat, lvl, domain = SemanticInvariantMiner.heuristic_classify(
        "Docker container images must not run as root user in production environments."
    )
    assert is_inv is True
    assert cat == ParsedConstraintCategory.ARCHITECTURE
    assert lvl == ParsedConstraintLevel.MUST_NOT
    assert domain == "deployment"

    # Architecture recommendation
    is_inv, cat, lvl, domain = SemanticInvariantMiner.heuristic_classify(
        "Components should communicate only through typed service interfaces."
    )
    assert is_inv is True
    assert cat == ParsedConstraintCategory.ARCHITECTURE
    assert lvl == ParsedConstraintLevel.SHOULD
    assert domain == "architecture"


def test_heuristic_classify_testing():
    """Verify testing directives."""
    is_inv, cat, lvl, domain = SemanticInvariantMiner.heuristic_classify(
        "Pull requests require 80% test coverage before merge."
    )
    assert is_inv is True
    assert cat == ParsedConstraintCategory.TESTING
    assert lvl == ParsedConstraintLevel.MUST
    assert domain == "testing"


def test_heuristic_classify_negative_filters():
    """Verify non-invariant text is excluded."""
    # Question
    is_inv, _, _, _ = SemanticInvariantMiner.heuristic_classify(
        "How do I set up local development?"
    )
    assert is_inv is False

    # Changelog entry
    is_inv, _, _, _ = SemanticInvariantMiner.heuristic_classify("Fixed bug in auth header parsing.")
    assert is_inv is False

    # Shell command
    is_inv, _, _, _ = SemanticInvariantMiner.heuristic_classify("npm install --save react")
    assert is_inv is False

    # Pure descriptive
    is_inv, _, _, _ = SemanticInvariantMiner.heuristic_classify(
        "This directory contains utilities for string manipulation."
    )
    assert is_inv is False


def test_candidate_sentence_extraction():
    """Verify markdown candidate extraction filters code blocks and headings."""
    doc = """# System Architecture

Here is an introductory paragraph that describes the platform.

```python
# Code block should be skipped
def run():
    print("test")
```

| Table | Header |
| --- | --- |
| row | value |

## Security Rules

- Enforce tenant isolation on every SQL query to prevent data leakage.
- Never write unencrypted secrets to disk.

### Notes
Just a brief note for operators.
"""
    candidates = EngineeringContextParser.extract_candidate_sentences(doc)
    # Code block and table rows skipped
    stmts = [c[2] for c in candidates]
    assert any("Enforce tenant isolation" in s for s in stmts)
    assert any("Never write unencrypted secrets" in s for s in stmts)
    assert not any("def run" in s for s in stmts)
    assert not any("Table" in s for s in stmts)
    assert not any("Security Rules" in s for s in stmts)


@pytest.mark.asyncio
async def test_invariant_miner_model_acceptance():
    """Verify System One decisions with confidence >= 0.85 are accepted."""
    mock_client = MockSystemOneClient(confidence_threshold=0.85)
    mock_client.set_response("q_0_is_inv", NoulAnswer(noul=0.96))
    mock_client.set_choice_response("q_0_category", "security", confidence=0.94)
    mock_client.set_choice_response("q_0_level", "must", confidence=0.92)

    miner = SemanticInvariantMiner(client=mock_client)
    constraints = await miner.mine_document(
        path="docs/SECURITY.md",
        content="All external API calls require authenticated token headers.",
    )

    assert len(constraints) == 1
    c = constraints[0]
    assert c.category == ParsedConstraintCategory.SECURITY
    assert c.level == ParsedConstraintLevel.MUST
    assert c.confidence == 0.96
    assert c.extra_metadata["source"] == "model"
    assert c.extra_metadata["domain"] == "security"


@pytest.mark.asyncio
async def test_invariant_miner_concurrency_mapping():
    """Verify concurrency domain maps to PERFORMANCE category."""
    mock_client = MockSystemOneClient(confidence_threshold=0.85)
    mock_client.set_response("q_0_is_inv", NoulAnswer(noul=0.95))
    mock_client.set_choice_response("q_0_category", "concurrency", confidence=0.90)
    mock_client.set_choice_response("q_0_level", "forbidden", confidence=0.89)

    miner = SemanticInvariantMiner(client=mock_client)
    constraints = await miner.mine_document(
        path="docs/CONCURRENCY.md",
        content="Deadlocks are strictly forbidden in transaction managers.",
    )

    assert len(constraints) == 1
    c = constraints[0]
    assert c.category == ParsedConstraintCategory.PERFORMANCE
    assert c.level == ParsedConstraintLevel.MUST_NOT
    assert c.extra_metadata["domain"] == "concurrency"


@pytest.mark.asyncio
async def test_invariant_miner_low_confidence_fallback():
    """Verify confidence < 0.85 triggers fallback to deterministic heuristic."""
    mock_client = MockSystemOneClient(confidence_threshold=0.85)
    # Model returns low confidence noul
    mock_client.set_response("q_0_is_inv", NoulAnswer(noul=0.55))

    miner = SemanticInvariantMiner(client=mock_client)
    # Sentence has clear imperative trigger "ensure" -> heuristic says True
    constraints = await miner.mine_document(
        path="docs/data.md",
        content="Always ensure database migrations are backward compatible.",
    )

    # Heuristic fallback accepts the constraint with source='fallback'
    assert len(constraints) == 1
    c = constraints[0]
    assert c.extra_metadata["source"] == "fallback"
    assert c.category == ParsedConstraintCategory.DATA_INTEGRITY
    assert c.level == ParsedConstraintLevel.MUST


@pytest.mark.asyncio
async def test_invariant_miner_offline_fallback():
    """Verify network error triggers graceful fallback without raising exceptions."""
    mock_client = MockSystemOneClient(offline=True)
    miner = SemanticInvariantMiner(client=mock_client)

    constraints = await miner.mine_document(
        path="docs/auth.md",
        content="Reject unauthenticated requests before routing to handler.",
    )

    assert len(constraints) == 1
    c = constraints[0]
    assert c.category == ParsedConstraintCategory.SECURITY
    assert c.extra_metadata["source"] == "fallback"


@pytest.mark.asyncio
async def test_invariant_miner_deduplication():
    """Verify miner skips sentences already extracted via RFC 2119 keywords."""
    existing = [
        ParsedConstraint(
            category=ParsedConstraintCategory.SECURITY,
            level=ParsedConstraintLevel.MUST,
            title="Sanitize inputs",
            statement="System MUST sanitize all user inputs.",
            source_path="docs/rules.md",
            line_start=1,
            line_end=1,
        )
    ]

    mock_client = MockSystemOneClient()
    miner = SemanticInvariantMiner(client=mock_client)

    content = """System MUST sanitize all user inputs.
Ensure all worker threads terminate cleanly upon SIGTERM.
"""
    constraints = await miner.mine_document(
        path="docs/rules.md",
        content=content,
        existing_constraints=existing,
    )

    # Line 1 is skipped because it's already in existing_constraints
    assert len(constraints) == 1
    assert "worker threads terminate" in constraints[0].statement


@pytest.mark.asyncio
async def test_evaluate_statement():
    """Verify single statement evaluation helper."""
    miner = SemanticInvariantMiner(client=MockSystemOneClient(enabled=False))
    c = await miner.evaluate_statement(
        "Enforce strict tenant isolation on every SQL query to prevent cross-tenant data leakage.",
        source_path="ARCHITECTURE.md",
    )
    assert c is not None
    assert c.category == ParsedConstraintCategory.SECURITY
    assert c.level == ParsedConstraintLevel.MUST
