import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_and_get_repository(client: AsyncClient):
    payload = {
        "owner": "testorg",
        "name": "testrepo",
        "full_name": "testorg/testrepo",
        "default_branch": "main",
    }
    response = await client.post("/api/v1/repositories/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["full_name"] == "testorg/testrepo"
    assert data["status"] == "idle"
    repo_id = data["id"]

    # Get repository by id
    get_res = await client.get(f"/api/v1/repositories/{repo_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == repo_id

    # List repositories
    list_res = await client.get("/api/v1/repositories/")
    assert list_res.status_code == 200
    repos = list_res.json()
    assert len(repos) == 1
    assert repos[0]["id"] == repo_id


@pytest.mark.asyncio
async def test_duplicate_repository_conflict(client: AsyncClient):
    payload = {
        "owner": "testorg",
        "name": "duprepo",
        "full_name": "testorg/duprepo",
        "default_branch": "main",
    }
    res1 = await client.post("/api/v1/repositories/", json=payload)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/repositories/", json=payload)
    assert res2.status_code == 409
