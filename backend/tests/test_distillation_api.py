import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_investigation_projection_and_reference_api(client: AsyncClient):
    # 1. Create a repository
    repo_payload = {
        "owner": "codeatlas",
        "name": "distill-test",
        "full_name": "codeatlas/distill-test",
        "default_branch": "main",
    }
    repo_res = await client.post("/api/v1/repositories/", json=repo_payload)
    assert repo_res.status_code == 201
    repo_id = repo_res.json()["id"]

    # 2. Create an investigation
    inv_payload = {
        "repository_id": repo_id,
        "query": "Refactor session timeout in backend/app/auth/session.py",
        "type": "before_change",
    }
    inv_res = await client.post("/api/v1/investigations/", json=inv_payload)
    assert inv_res.status_code == 201
    inv_id = inv_res.json()["id"]

    # 3. Run investigation (uses MockLLMProvider deterministically)
    run_res = await client.post(
        f"/api/v1/investigations/{inv_id}/run",
        json={"target_path": "backend/app/auth/session.py"},
    )
    assert run_res.status_code == 200
    run_data = run_res.json()
    assert run_data["status"] == "completed"

    # 4. Fetch JSON projection (unconstrained)
    proj_json_res = await client.get(f"/api/v1/investigations/{inv_id}/projection?format=json")
    assert proj_json_res.status_code == 200
    json_data = proj_json_res.json()
    assert json_data["investigation_id"] == inv_id
    assert json_data["format"] == "json"
    assert json_data["is_distilled"] is False
    assert json_data["content_json"]["_schema"] == "codeatlas.pre_change_brief.v1"
    assert "risk" in json_data["content_json"]

    # 5. Fetch Markdown projection (unconstrained)
    proj_md_res = await client.get(f"/api/v1/investigations/{inv_id}/projection?format=markdown")
    assert proj_md_res.status_code == 200
    md_data = proj_md_res.json()
    assert md_data["format"] == "markdown"
    assert "Pre-Change Investigation Brief" in md_data["content_text"]

    # 6. Fetch distilled projection under tight token budget
    proj_budget_res = await client.get(
        f"/api/v1/investigations/{inv_id}/projection?format=markdown&token_budget=150"
    )
    assert proj_budget_res.status_code == 200
    budget_data = proj_budget_res.json()
    assert budget_data["is_distilled"] is True
    assert budget_data["token_budget"] == 150
    assert budget_data["shed_tier"] >= 1

    # 7. Test reference endpoint if any omissions registered, or test evidence fallback
    import urllib.parse

    if budget_data["omissions"]:
        first_omission = budget_data["omissions"][0]
        ref_id = first_omission["ref_id"]
        quoted = urllib.parse.quote(ref_id, safe="")
        ref_res = await client.get(f"/api/v1/investigations/{inv_id}/references/{quoted}")
        assert ref_res.status_code == 200
        ref_data = ref_res.json()
        assert ref_data["ref_id"] == ref_id
        assert "original_payload" in ref_data

        # Also test via query param alias
        alias_res = await client.get(
            f"/api/v1/investigations/{inv_id}/reference", params={"ref_id": ref_id}
        )
        assert alias_res.status_code == 200
        assert alias_res.json()["ref_id"] == ref_id

    # 8. Test 404 for invalid reference
    not_found_res = await client.get(
        f"/api/v1/investigations/{inv_id}/references/{urllib.parse.quote('ref#unknown-nonexistent-123', safe='')}"
    )
    assert not_found_res.status_code == 404

    # 9. Test 404 for nonexistent investigation
    fake_id = str(uuid.uuid4())
    fake_res = await client.get(f"/api/v1/investigations/{fake_id}/projection")
    assert fake_res.status_code == 404


@pytest.mark.asyncio
async def test_investigation_decomposition_endpoint(client: AsyncClient):
    # 1. Create a repository
    repo_res = await client.post(
        "/api/v1/repositories/",
        json={
            "owner": "codeatlas",
            "name": "decomp-api-test",
            "full_name": "codeatlas/decomp-api-test",
            "default_branch": "main",
        },
    )
    assert repo_res.status_code == 201
    repo_id = repo_res.json()["id"]

    # 2. Create an investigation with multi-file disjoint change
    inv_res = await client.post(
        "/api/v1/investigations/",
        json={
            "repository_id": repo_id,
            "query": "Modify auth in backend/app/auth/router.py and billing in backend/app/billing/charge.py",
            "type": "before_change",
        },
    )
    assert inv_res.status_code == 201
    inv_id = inv_res.json()["id"]

    # 3. Run investigation
    run_res = await client.post(f"/api/v1/investigations/{inv_id}/run", json={})
    assert run_res.status_code == 200

    # 4. Fetch decomposition endpoint
    decomp_res = await client.get(f"/api/v1/investigations/{inv_id}/decomposition")
    assert decomp_res.status_code == 200
    decomp_data = decomp_res.json()

    assert decomp_data["total_files"] == 2
    assert decomp_data["component_count"] == 2
    assert decomp_data["is_decomposable"] is True
    assert len(decomp_data["clusters"]) == 2
    assert "suggested_pr_title" in decomp_data["clusters"][0]
    assert "suggested_branch_name" in decomp_data["clusters"][0]

    # 5. Test 404 for nonexistent investigation
    fake_id = str(uuid.uuid4())
    not_found = await client.get(f"/api/v1/investigations/{fake_id}/decomposition")
    assert not_found.status_code == 404


@pytest.mark.asyncio
async def test_investigation_ownership_endpoint(client: AsyncClient):
    # 1. Create a repository
    repo_res = await client.post(
        "/api/v1/repositories/",
        json={
            "owner": "codeatlas",
            "name": "ownership-api-test",
            "full_name": "codeatlas/ownership-api-test",
            "default_branch": "main",
        },
    )
    assert repo_res.status_code == 201
    repo_id = repo_res.json()["id"]

    # 2. Ingest commit with file change
    commit_res = await client.post(
        f"/api/v1/repositories/{repo_id}/commits/ingest",
        json={
            "commits": [
                {
                    "commit_hash": "b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0",
                    "author_name": "Charlie Maintainer",
                    "author_email": "charlie@example.com",
                    "committed_at": "2026-09-20T10:00:00Z",
                    "message": "feat: init payments service",
                    "file_changes": [
                        {
                            "file_path": "backend/app/payments/service.py",
                            "change_type": "added",
                            "insertions": 200,
                            "deletions": 10,
                        }
                    ],
                }
            ]
        },
    )
    assert commit_res.status_code == 200

    # 3. Create an investigation
    inv_res = await client.post(
        "/api/v1/investigations/",
        json={
            "repository_id": repo_id,
            "query": "Refactor webhook handling in backend/app/payments/service.py",
            "type": "before_change",
        },
    )
    assert inv_res.status_code == 201
    inv_id = inv_res.json()["id"]

    # 4. Run investigation
    run_res = await client.post(
        f"/api/v1/investigations/{inv_id}/run",
        json={"target_path": "backend/app/payments/service.py"},
    )
    assert run_res.status_code == 200

    # 5. Fetch ownership endpoint
    own_res = await client.get(f"/api/v1/investigations/{inv_id}/ownership")
    assert own_res.status_code == 200
    own_data = own_res.json()

    assert own_data["target_files"] == ["backend/app/payments/service.py"]
    assert own_data["overall_bus_factor"] == 1
    assert len(own_data["file_ownerships"]) >= 1
    assert own_data["file_ownerships"][0]["file_path"] == "backend/app/payments/service.py"
    assert own_data["file_ownerships"][0]["primary_owner"]["author_name"] == "Charlie Maintainer"
    assert len(own_data["recommended_reviewers"]) >= 1
    assert own_data["recommended_reviewers"][0]["author_name"] == "Charlie Maintainer"

    # 6. Test 404 for nonexistent investigation
    fake_id = str(uuid.uuid4())
    not_found = await client.get(f"/api/v1/investigations/{fake_id}/ownership")
    assert not_found.status_code == 404
