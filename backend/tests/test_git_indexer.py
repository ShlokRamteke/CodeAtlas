from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.history.git_indexer import (
    ChangeType,
    GitHistoryIndexer,
    ParsedCommit,
    ParsedFileChange,
)
from app.models.repository import Repository


@pytest.mark.asyncio
async def test_git_indexer_index_and_file_history(db_session: AsyncSession) -> None:
    # 1. Create a repository
    repo = Repository(
        id=uuid.uuid4(),
        owner="test-owner",
        name="git-repo",
        full_name="test-owner/git-repo",
        default_branch="main",
    )
    db_session.add(repo)
    await db_session.commit()

    # 2. Build parsed commits
    indexer = GitHistoryIndexer()
    commits = [
        ParsedCommit(
            commit_hash="commit_001",
            author_name="Alice",
            author_email="alice@test.com",
            committed_at=datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            message="feat: initial PaymentService introduction",
            file_changes=[
                ParsedFileChange(
                    file_path="src/services/PaymentService.ts",
                    change_type=ChangeType.ADDED,
                    insertions=50,
                    deletions=0,
                )
            ],
        ),
        ParsedCommit(
            commit_hash="commit_002",
            author_name="Bob",
            author_email="bob@test.com",
            committed_at=datetime(2025, 2, 1, 14, 0, 0, tzinfo=timezone.utc),
            message="refactor: update Stripe refund logic in PaymentService",
            file_changes=[
                ParsedFileChange(
                    file_path="src/services/PaymentService.ts",
                    change_type=ChangeType.MODIFIED,
                    insertions=12,
                    deletions=4,
                )
            ],
        ),
    ]

    # Index commits
    count = await indexer.index_commits(repo.id, commits, db_session)
    assert count == 2

    # 3. Query file history
    file_history = await indexer.get_file_history(repo.id, "src/services/PaymentService.ts", db_session)
    assert file_history.total_commits == 2
    assert len(file_history.commits) == 2
    assert file_history.introducing_commit is not None
    assert file_history.introducing_commit["commit_hash"] == "commit_001"
    assert file_history.introducing_commit["author_name"] == "Alice"
    assert len(file_history.authors) == 2


@pytest.mark.asyncio
async def test_git_indexer_component_history(db_session: AsyncSession) -> None:
    repo = Repository(
        id=uuid.uuid4(),
        owner="test-owner",
        name="comp-repo",
        full_name="test-owner/comp-repo",
        default_branch="main",
    )
    db_session.add(repo)
    await db_session.commit()

    indexer = GitHistoryIndexer()
    payload = [
        {
            "commit_hash": "c1",
            "author_name": "Carol",
            "author_email": "carol@test.com",
            "committed_at": "2025-01-10T12:00:00Z",
            "message": "feat: order processing",
            "file_changes": [
                {"file_path": "src/orders/service.ts", "change_type": "added", "insertions": 30, "deletions": 0},
                {"file_path": "src/orders/model.ts", "change_type": "added", "insertions": 20, "deletions": 0},
            ],
        }
    ]
    parsed = indexer.parse_synthetic_payload(payload)
    await indexer.index_commits(repo.id, parsed, db_session)

    comp_res = await indexer.get_component_history(repo.id, "src/orders", db_session)
    assert comp_res["total_commits"] == 1
    assert comp_res["introducing_commit"]["commit_hash"] == "c1"
    assert len(comp_res["files_touched"]) == 2
