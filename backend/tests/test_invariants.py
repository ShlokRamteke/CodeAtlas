from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.investigation.invariants import (
    InvariantSynthesizer,
)
from app.models.engineering_doc import ADRStatus


def test_resolve_governing_status_accepted() -> None:
    status, superseded_by = InvariantSynthesizer.resolve_governing_status(
        doc_status=ADRStatus.ACCEPTED,
        doc_path="docs/adr/0001-record-architecture.md",
        doc_title="ADR-001: Record Architecture",
        raw_content="All services must use PostgreSQL transactions.",
        all_docs=[],
    )
    assert status == "governing"
    assert superseded_by is None


def test_resolve_governing_status_explicit_superseded() -> None:
    status, superseded_by = InvariantSynthesizer.resolve_governing_status(
        doc_status=ADRStatus.SUPERSEDED,
        doc_path="docs/adr/0002-in-memory-cache.md",
        doc_title="ADR-002: In-Memory Cache",
        raw_content="Status: Superseded by [ADR-004]\nThis cache was replaced.",
        all_docs=[],
    )
    assert status == "superseded"
    assert superseded_by == "ADR-004"


def test_resolve_governing_status_cross_adr_supersedes() -> None:
    doc_a = {
        "path": "docs/adr/0001-raw-threads.md",
        "title": "ADR-001: Raw OS Threads",
        "status": ADRStatus.ACCEPTED,
        "raw_content": "We use raw OS threads for background workers.",
    }
    doc_b = {
        "path": "docs/adr/0003-asyncio-tasks.md",
        "title": "ADR-003: Asyncio Workers",
        "status": ADRStatus.ACCEPTED,
        "raw_content": "Status: Accepted\nSupersedes [ADR-001]\nWe migrate to asyncio.",
    }

    all_docs = [doc_a, doc_b]

    status, superseded_by = InvariantSynthesizer.resolve_governing_status(
        doc_status=doc_a["status"],
        doc_path=doc_a["path"],
        doc_title=doc_a["title"],
        raw_content=doc_a["raw_content"],
        all_docs=all_docs,
    )
    assert status == "superseded"
    assert superseded_by == "ADR-003: Asyncio Workers"


@pytest.mark.asyncio
async def test_extract_origin_intent_in_memory() -> None:
    target_files = ["app/auth/jwt.py", "app/auth/session.py"]
    mock_commits = [
        {
            "hash": "commit_recent_123",
            "message": "Refactor session timeout",
            "author": "Alice",
            "committed_at": datetime(2026, 8, 1, tzinfo=timezone.utc),
        },
        {
            "hash": "commit_origin_456",
            "message": "Initial JWT authentication setup (Fixes #42)",
            "author": "Bob",
            "committed_at": datetime(2026, 1, 15, tzinfo=timezone.utc),
        },
    ]

    intent_map = await InvariantSynthesizer.extract_origin_intent_for_targets(
        db=None,
        repository_id=uuid.uuid4(),
        target_files=target_files,
        file_commits=mock_commits,
    )

    assert "app/auth/jwt.py" in intent_map
    info = intent_map["app/auth/jwt.py"]
    assert info["commit_hash"] == "commit_origin_456"
    assert info["pr_number"] == 42
    assert info["author"] == "Bob"


@pytest.mark.asyncio
async def test_synthesize_invariants_with_docs() -> None:
    repo_id = uuid.uuid4()
    target_files = ["backend/app/auth/token.py"]
    target_symbols = ["validate_token"]

    mock_docs = [
        {
            "path": "docs/adr/0001-token-security.md",
            "title": "ADR-001: Token Security Architecture",
            "raw_content": (
                "# ADR-001: Token Security Architecture\n"
                "Status: Accepted\n"
                "## Context\n"
                "Token verification must never bypass signature validation.\n"
                "All token authentication handlers should enforce strict 15-minute expirations.\n"
            ),
        },
        {
            "path": "docs/adr/0002-legacy-cookies.md",
            "title": "ADR-002: Legacy Session Cookies",
            "raw_content": (
                "# ADR-002: Legacy Session Cookies\n"
                "Status: Superseded by [ADR-001]\n"
                "Legacy sessions must store raw cookie tokens.\n"
            ),
        },
    ]

    mock_commits = [
        {
            "hash": "c0ffee123456789",
            "message": "Implement token validation endpoint (PR #88)",
            "author": "Carol",
            "committed_at": datetime(2026, 3, 10, tzinfo=timezone.utc),
        }
    ]

    invariants = await InvariantSynthesizer.synthesize_invariants(
        repository_id=repo_id,
        target_files=target_files,
        target_symbols=target_symbols,
        db=None,
        engineering_docs=mock_docs,
        file_commits=mock_commits,
    )

    assert len(invariants) >= 2
    gov_invs = [inv for inv in invariants if inv.governing_status == "governing"]
    sup_invs = [inv for inv in invariants if inv.governing_status == "superseded"]

    assert len(gov_invs) >= 1
    assert any(
        "must never" in inv.statement.lower() or "signature" in inv.statement.lower()
        for inv in gov_invs
    )

    # Check origin intent linkage
    first_gov = gov_invs[0]
    assert first_gov.origin_commit_hash == "c0ffee123456789"
    assert first_gov.origin_pr_number == 88
    assert "PR #88" in first_gov.rationale
    assert first_gov.level in ("must", "must_not", "should")

    # Check superseded invariant
    assert len(sup_invs) >= 1
    sup_one = sup_invs[0]
    assert sup_one.superseded_by == "ADR-001"
    assert "SUPERSEDED" in sup_one.rationale


@pytest.mark.asyncio
async def test_synthesize_invariants_empty() -> None:
    invariants = await InvariantSynthesizer.synthesize_invariants(
        repository_id=uuid.uuid4(),
        target_files=["some/file.py"],
        target_symbols=[],
        db=None,
        engineering_docs=[],
        file_commits=[],
    )
    assert invariants == []
