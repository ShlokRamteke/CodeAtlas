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

    # 2. Ingest PRs
    prs_payload = [
        {
            "number": 10,
            "title": "feat(auth): initial AuthService implementation",
            "body": "Implements authentication.\n\nCloses #50",
            "state": "merged",
            "author": "Dave Developer",
            "merged_at": "2025-01-05T10:00:00Z",
            "labels": ["feature", "auth"],
            "html_url": "https://github.com/api-test/history-app/pull/10",
        },
        {
            "number": 11,
            "title": "fix(auth): handle expired token edge-case",
            "body": "Fixes #51",
            "state": "merged",
            "author": "Eve Engineer",
            "merged_at": "2025-02-15T15:00:00Z",
            "labels": ["bug"],
            "html_url": "https://github.com/api-test/history-app/pull/11",
        },
    ]
    pr_res = await client.post(
        f"/api/v1/repositories/{repo_id}/pull-requests/ingest",
        json={"pull_requests": prs_payload},
    )
    assert pr_res.status_code == 200
    assert pr_res.json()["indexed_count"] == 2

    # 3. Ingest Issues
    issues_payload = [
        {
            "number": 50,
            "title": "Need authentication for user sessions",
            "body": "Design auth service.",
            "state": "closed",
            "author": "product-mgr",
            "closed_at": "2025-01-05T10:00:00Z",
            "labels": ["security"],
            "html_url": "https://github.com/api-test/history-app/issues/50",
        },
        {
            "number": 51,
            "title": "Expired token causes infinite redirect loop",
            "body": "Handle 401 correctly.",
            "state": "closed",
            "author": "qa-engineer",
            "closed_at": "2025-02-15T15:00:00Z",
            "labels": ["bug"],
            "html_url": "https://github.com/api-test/history-app/issues/51",
        },
    ]
    issue_res = await client.post(
        f"/api/v1/repositories/{repo_id}/issues/ingest",
        json={"issues": issues_payload},
    )
    assert issue_res.status_code == 200
    assert issue_res.json()["indexed_count"] == 2

    # 4. Ingest commit payload with PR & Issue references
    commits_payload = [
        {
            "commit_hash": "sha_111",
            "author_name": "Dave Developer",
            "author_email": "dave@corp.com",
            "committed_at": "2025-01-05T10:00:00Z",
            "message": "feat(auth): initial AuthService implementation (PR #10) - fixes #50",
            "file_changes": [
                {
                    "file_path": "src/auth/AuthService.ts",
                    "change_type": "added",
                    "insertions": 40,
                    "deletions": 0,
                }
            ],
        },
        {
            "commit_hash": "sha_222",
            "author_name": "Eve Engineer",
            "author_email": "eve@corp.com",
            "committed_at": "2025-02-15T15:00:00Z",
            "message": "Merge pull request #11 from fix/token\n\nFixes #51",
            "file_changes": [
                {
                    "file_path": "src/auth/AuthService.ts",
                    "change_type": "modified",
                    "insertions": 5,
                    "deletions": 2,
                }
            ],
        },
    ]

    ingest_res = await client.post(
        f"/api/v1/repositories/{repo_id}/commits/ingest",
        json={"commits": commits_payload},
    )
    assert ingest_res.status_code == 200
    assert ingest_res.json()["indexed_count"] == 2

    # 5. List commits (verify linked PRs & Issues)
    list_res = await client.get(f"/api/v1/repositories/{repo_id}/commits")
    assert list_res.status_code == 200
    commits_list = list_res.json()
    assert len(commits_list) == 2
    assert commits_list[0]["commit_hash"] == "sha_222"
    assert len(commits_list[0]["linked_pull_requests"]) == 1
    assert commits_list[0]["linked_pull_requests"][0]["pr_number"] == 11
    assert (
        commits_list[0]["linked_pull_requests"][0]["title"]
        == "fix(auth): handle expired token edge-case"
    )

    # 6. List Pull Requests
    prs_res = await client.get(f"/api/v1/repositories/{repo_id}/pull-requests")
    assert prs_res.status_code == 200
    prs_data = prs_res.json()
    assert len(prs_data) == 2
    pr_10 = next(p for p in prs_data if p["number"] == 10)
    assert len(pr_10["linked_issues"]) == 1
    assert pr_10["linked_issues"][0]["issue_number"] == 50

    # 7. List Issues
    issues_res = await client.get(f"/api/v1/repositories/{repo_id}/issues")
    assert issues_res.status_code == 200
    issues_data = issues_res.json()
    assert len(issues_data) == 2

    # 8. Full Provenance Trace
    trace_res = await client.get(f"/api/v1/repositories/{repo_id}/trace/src/auth/AuthService.ts")
    assert trace_res.status_code == 200
    trace = trace_res.json()
    assert trace["file_path"] == "src/auth/AuthService.ts"
    assert trace["total_commits"] == 2
    assert trace["total_pull_requests"] == 2
    assert trace["total_issues"] == 2
    assert len(trace["trace_chain"]) == 2
