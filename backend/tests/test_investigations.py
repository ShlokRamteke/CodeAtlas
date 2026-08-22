import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_get_investigation(client: AsyncClient):
    repo_payload = {
        "owner": "archaeologist",
        "name": "core",
        "full_name": "archaeologist/core",
        "default_branch": "main",
    }
    repo_res = await client.post("/api/v1/repositories/", json=repo_payload)
    assert repo_res.status_code == 201
    repo_id = repo_res.json()["id"]

    inv_payload = {
        "repository_id": repo_id,
        "query": "Why does the caching middleware retry 3 times?",
        "type": "why",
    }
    inv_res = await client.post("/api/v1/investigations/", json=inv_payload)
    assert inv_res.status_code == 201
    inv_data = inv_res.json()
    assert inv_data["query"] == inv_payload["query"]
    assert inv_data["type"] == "why"
    assert inv_data["status"] == "pending"
    inv_id = inv_data["id"]

    # Fetch investigation
    get_res = await client.get(f"/api/v1/investigations/{inv_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == inv_id

    # List repo investigations
    list_res = await client.get(f"/api/v1/investigations/repository/{repo_id}")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1
