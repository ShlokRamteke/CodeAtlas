from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_history_api_endpoints(client: AsyncClient) -> None:
    # 1. Create repo
    create_res = await client.post(
        "/api/v1/repositories/",
        json={"owner": "api-test", "name": "history-app", "full_name": "api-test/history-app"},
    )
    assert create_res.status_code == 201
    repo_id = create_res.json()["id"]

    # 2. Ingest commit payload
    commits_payload = [
        {
            "commit_hash": "sha_111",
            "author_name": "Dave Developer",
            "author_email": "dave@corp.com",
            "committed_at": "2025-01-05T10:00:00Z",
            "message": "feat(auth): initial AuthService implementation",
            "file_changes": [
                {"file_path": "src/auth/AuthService.ts", "change_type": "added", "insertions": 40, "deletions": 0}
            ],
        },
        {
            "commit_hash": "sha_222",
            "author_name": "Eve Engineer",
            "author_email": "eve@corp.com",
            "committed_at": "2025-02-15T15:00:00Z",
            "message": "fix(auth): handle expired token edge-case",
            "file_changes": [
                {"file_path": "src/auth/AuthService.ts", "change_type": "modified", "insertions": 5, "deletions": 2}
            ],
        },
    ]

    ingest_res = await client.post(
        f"/api/v1/repositories/{repo_id}/commits/ingest",
        json={"commits": commits_payload},
    )
    assert ingest_res.status_code == 200
    assert ingest_res.json()["indexed_count"] == 2

    # 3. List commits
    list_res = await client.get(f"/api/v1/repositories/{repo_id}/commits")
    assert list_res.status_code == 200
    commits_list = list_res.json()
    assert len(commits_list) == 2
    assert commits_list[0]["commit_hash"] == "sha_222"

    # 4. Get single commit
    detail_res = await client.get(f"/api/v1/repositories/{repo_id}/commits/sha_111")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["author_name"] == "Dave Developer"
    assert len(detail["file_changes"]) == 1

    # 5. File History & Introducing Commit
    file_res = await client.get(f"/api/v1/repositories/{repo_id}/files/src/auth/AuthService.ts/history")
    assert file_res.status_code == 200
    file_data = file_res.json()
    assert file_data["total_commits"] == 2
    assert file_data["introducing_commit"]["commit_hash"] == "sha_111"
    assert file_data["introducing_commit"]["author_name"] == "Dave Developer"

    # 6. Component History
    comp_res = await client.get(f"/api/v1/repositories/{repo_id}/components/src/auth/history")
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert comp_data["total_commits"] == 2
    assert comp_data["introducing_commit"]["commit_hash"] == "sha_111"
