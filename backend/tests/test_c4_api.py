from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_c4_architecture_and_export_endpoints(client: AsyncClient):
    # 1. Create test repository
    payload = {
        "owner": "testorg",
        "name": "c4repo",
        "full_name": "testorg/c4repo",
        "default_branch": "main",
    }
    create_res = await client.post("/api/v1/repositories/", json=payload)
    assert create_res.status_code == 201
    repo_id = create_res.json()["id"]

    # Ingest mock files
    files_payload = {
        "files": {
            "frontend/src/App.tsx": "export function App() { return <div>App</div>; }",
            "backend/app/main.py": "from app.models import User\ndef run(): pass\n",
            "backend/app/models.py": "class User:\n    pass\n",
        }
    }
    ingest_res = await client.post(f"/api/v1/repositories/{repo_id}/ingest", json=files_payload)
    assert ingest_res.status_code == 200

    # 2. Test GET /api/v1/repositories/{id}/architecture/c4
    c4_res = await client.get(f"/api/v1/repositories/{repo_id}/architecture/c4")
    assert c4_res.status_code == 200
    data = c4_res.json()

    assert data["repository_id"] == repo_id
    assert data["system_name"] == "c4repo"
    assert len(data["containers"]) >= 2
    assert "diagrams" in data
    assert "C4Context" in data["diagrams"]["context_mermaid"]
    assert "C4Container" in data["diagrams"]["container_mermaid"]
    assert "flowchart TB" in data["diagrams"]["flowchart_mermaid"]
    assert "# c4repo — Architectural Specification" in data["markdown_export"]

    # 3. Test GET /api/v1/repositories/{id}/architecture/export?format=markdown
    md_res = await client.get(f"/api/v1/repositories/{repo_id}/architecture/export?format=markdown")
    assert md_res.status_code == 200
    assert md_res.headers["content-type"].startswith("text/markdown")
    assert "# c4repo — Architectural Specification" in md_res.text

    # 4. Test GET /api/v1/repositories/{id}/architecture/export?format=mermaid
    mmd_res = await client.get(f"/api/v1/repositories/{repo_id}/architecture/export?format=mermaid")
    assert mmd_res.status_code == 200
    assert "flowchart TB" in mmd_res.text

    # 5. Test GET /api/v1/repositories/{id}/architecture/export?format=json
    json_res = await client.get(f"/api/v1/repositories/{repo_id}/architecture/export?format=json")
    assert json_res.status_code == 200
    json_data = json_res.json()
    assert json_data["system_name"] == "c4repo"
    assert len(json_data["containers"]) >= 2
