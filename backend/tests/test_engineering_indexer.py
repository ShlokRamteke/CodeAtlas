from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.history.engineering_indexer import EngineeringContextIndexer
from app.models.design_constraint import ConstraintCategory, ConstraintLevel
from app.models.engineering_doc import ADRStatus, EngineeringDocType
from app.models.repository import Repository


@pytest.mark.asyncio
async def test_engineering_context_indexer_flow(db_session: AsyncSession) -> None:
    # 1. Setup repository
    repo = Repository(
        owner="test-org",
        name="secure-core",
        full_name="test-org/secure-core",
    )
    db_session.add(repo)
    await db_session.commit()
    await db_session.refresh(repo)

    indexer = EngineeringContextIndexer(db_session)

    # 2. Index README
    readme_content = """# Secure Core Platform
High performance cryptographic kernel.

## Architecture
- All API handlers MUST validate tenant isolation tokens.
- Never log plaintext secrets or unencrypted keys to stdout.
"""
    doc_readme = await indexer.index_document(repo.id, "README.md", readme_content)
    assert doc_readme.doc_type == EngineeringDocType.README
    assert doc_readme.title == "Secure Core Platform"

    # Verify constraints created
    constraints = await indexer.get_constraints(repo.id)
    assert len(constraints) == 2
    assert any(c.category == ConstraintCategory.SECURITY for c in constraints)
    assert any(c.level == ConstraintLevel.MUST_NOT for c in constraints)

    # 3. Index ADR
    adr_content = """# 0001: Use AES-256-GCM for Data Encryption

## Status
Accepted

## Deciders
Security Guild

## Context
We require authenticated encryption.

## Decision
The system MUST use AES-256-GCM with distinct nonces.
"""
    doc_adr = await indexer.index_document(repo.id, "docs/adr/0001-encryption.md", adr_content)
    assert doc_adr.doc_type == EngineeringDocType.ADR
    assert doc_adr.status == ADRStatus.ACCEPTED
    assert doc_adr.deciders == "Security Guild"

    # Verify ADR query
    adrs = await indexer.get_adrs(repo.id, status=ADRStatus.ACCEPTED)
    assert len(adrs) == 1
    assert adrs[0].title == "0001: Use AES-256-GCM for Data Encryption"

    # 4. Search engineering context
    search_res = await indexer.search_engineering_context(repo.id, query="AES encryption")
    assert search_res["total_matches"] > 0
    assert any("AES" in d["title"] for d in search_res["docs"])

    # 5. Bulk index files
    files = {
        "ARCHITECTURE.md": """# System Architecture\n- Modules MUST communicate through contracts.""",
        "TESTING.md": """# Test Rules\n- Unit tests SHOULD maintain at least 80% coverage.""",
    }
    bulk_docs = await indexer.index_repository_docs(repo.id, files)
    assert len(bulk_docs) == 2

    # Verify all docs count
    all_docs = await indexer.get_docs(repo.id)
    assert len(all_docs) == 4  # README, ADR, ARCHITECTURE, TESTING
