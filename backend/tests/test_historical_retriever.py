from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.history.git_indexer import GitHistoryIndexer
from app.history.historical_linker import HistoricalLinker
from app.history.retriever import HistoricalRetriever
from app.models.repository import Repository
from app.models.source_file import SourceFile
from app.models.symbol import Symbol, SymbolKind
from app.schemas.history import HistoricalRetrievalRequest


@pytest.mark.asyncio
async def test_historical_retriever_search_and_ranking(db_session: AsyncSession) -> None:
    # 1. Setup repository
    repo = Repository(
        owner="retriever-test",
        name="crypto-vault",
        full_name="retriever-test/crypto-vault",
    )
    db_session.add(repo)
    await db_session.commit()
    await db_session.refresh(repo)

    # 2. Ingest PRs & Issues
    linker = HistoricalLinker()
    parsed_prs = linker.parse_synthetic_prs(
        [
            {
                "number": 42,
                "title": "feat(vault): add hardware security module (HSM) signing support",
                "body": "Implements HSM key derivation.\n\nFixes #101",
                "state": "merged",
                "author": "Alice Crypto",
                "merged_at": "2025-03-01T12:00:00Z",
                "labels": ["security", "hsm"],
                "html_url": "https://github.com/test/pull/42",
            },
            {
                "number": 43,
                "title": "fix(vault): patch memory leak in key rotation cache",
                "body": "Resolves #102",
                "state": "closed",
                "author": "Bob Security",
                "closed_at": "2025-04-01T12:00:00Z",
                "labels": ["bug"],
                "html_url": "https://github.com/test/pull/43",
            },
        ]
    )
    await linker.index_pull_requests(repo.id, parsed_prs, db_session)

    parsed_issues = linker.parse_synthetic_issues(
        [
            {
                "number": 101,
                "title": "Support PKCS#11 hardware security modules for key signing",
                "body": "Need hardware token support.",
                "state": "closed",
                "author": "auditor",
                "closed_at": "2025-03-01T12:00:00Z",
                "labels": ["compliance"],
                "html_url": "https://github.com/test/issues/101",
            },
            {
                "number": 102,
                "title": "Key rotation cache retains orphaned session descriptors",
                "body": "Memory leaks over time.",
                "state": "closed",
                "author": "sre",
                "closed_at": "2025-04-01T12:00:00Z",
                "labels": ["perf"],
                "html_url": "https://github.com/test/issues/102",
            },
        ]
    )
    await linker.index_issues(repo.id, parsed_issues, db_session)

    # 3. Ingest Commits with file changes
    indexer = GitHistoryIndexer()
    parsed_commits = indexer.parse_synthetic_payload(
        [
            {
                "commit_hash": "c001_intro",
                "author_name": "Alice Crypto",
                "author_email": "alice@vault.io",
                "committed_at": "2025-03-01T12:00:00Z",
                "message": "feat(vault): introduce HSMSigner class (PR #42) - fixes #101",
                "file_changes": [
                    {
                        "file_path": "src/vault/HSMSigner.ts",
                        "change_type": "added",
                        "insertions": 120,
                        "deletions": 0,
                    },
                    {
                        "file_path": "src/vault/KeyStore.ts",
                        "change_type": "modified",
                        "insertions": 15,
                        "deletions": 2,
                    },
                ],
            },
            {
                "commit_hash": "c002_rotation",
                "author_name": "Bob Security",
                "author_email": "bob@vault.io",
                "committed_at": "2025-04-01T12:00:00Z",
                "message": "fix(vault): optimize KeyStore key rotation cache (#43)",
                "file_changes": [
                    {
                        "file_path": "src/vault/KeyStore.ts",
                        "change_type": "modified",
                        "insertions": 30,
                        "deletions": 10,
                    }
                ],
            },
        ]
    )
    await indexer.index_commits(repo.id, parsed_commits, db_session)

    # 4. Add SourceFile & Symbol for symbol-level test

    src_file = SourceFile(
        repository_id=repo.id,
        path="src/vault/HSMSigner.ts",
        language="typescript",
        content_hash="hash_hsm",
        size_bytes=2400,
    )
    db_session.add(src_file)
    await db_session.commit()
    await db_session.refresh(src_file)

    sym = Symbol(
        file_id=src_file.id,
        repository_id=repo.id,
        name="HSMSigner",
        kind=SymbolKind.CLASS,
        line_start=10,
        line_end=85,
        signature="export class HSMSigner implements ISigner",
    )
    db_session.add(sym)
    await db_session.commit()

    retriever = HistoricalRetriever()

    # Test 1: Commit search by query, author, and path
    res_commits = await retriever.search_commits(
        repository_id=repo.id,
        db=db_session,
        query="HSMSigner",
    )
    assert len(res_commits) == 1
    assert res_commits[0].commit_hash == "c001_intro"

    res_author = await retriever.search_commits(
        repository_id=repo.id,
        db=db_session,
        author="Bob",
    )
    assert len(res_author) == 1
    assert res_author[0].commit_hash == "c002_rotation"

    res_path = await retriever.search_commits(
        repository_id=repo.id,
        db=db_session,
        file_path="src/vault/KeyStore.ts",
    )
    assert len(res_path) == 2

    # Test 2: Search PRs by query and label
    res_prs = await retriever.search_pull_requests(
        repository_id=repo.id,
        db=db_session,
        query="hardware",
    )
    assert len(res_prs) == 1
    assert res_prs[0].number == 42

    res_pr_label = await retriever.search_pull_requests(
        repository_id=repo.id,
        db=db_session,
        label="bug",
    )
    assert len(res_pr_label) == 1
    assert res_pr_label[0].number == 43

    # Test 3: Search Issues by keyword and status
    res_issues = await retriever.search_issues(
        repository_id=repo.id,
        db=db_session,
        query="memory leak",
    )
    assert len(res_issues) == 1
    assert res_issues[0].number == 102

    # Test 4: Symbol History Extraction
    sym_history = await retriever.retrieve_symbol_history(
        repository_id=repo.id,
        symbol_name="HSMSigner",
        db=db_session,
    )
    assert sym_history is not None
    assert sym_history.symbol_name == "HSMSigner"
    assert sym_history.file_path == "src/vault/HSMSigner.ts"
    assert sym_history.introducing_commit is not None
    assert sym_history.introducing_commit["commit_hash"] == "c001_intro"
    assert len(sym_history.evolution_timeline) == 1
    assert sym_history.evolution_timeline[0]["event_type"] == "introduction"

    # Test 5: Ranked Deterministic Evidence Retrieval
    retrieval_req = HistoricalRetrievalRequest(
        query="HSMSigner",
        component_path="src/vault",
        limit=10,
    )
    evidence_res = await retriever.retrieve_historical_evidence(
        repository_id=repo.id,
        req=retrieval_req,
        db=db_session,
    )

    assert evidence_res.total_evidence_count > 0
    assert len(evidence_res.evidence) > 0
    top_ev = evidence_res.evidence[0]
    assert top_ev.score >= 0.8
    assert "HSMSigner" in top_ev.title or "HSMSigner" in top_ev.snippet
    assert "commit:c001_in" in top_ev.citations[0]
    assert "pr:#42" in top_ev.citations or "issue:#101" in top_ev.citations
    assert "Found" in evidence_res.summary
