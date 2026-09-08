from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_engineering_api_endpoints(client: AsyncClient) -> None:
    # 1. Create repo
    create_res = await client.post(
        "/api/v1/repositories/",
        json={"owner": "api-test", "name": "eng-app", "full_name": "api-test/eng-app"},
    )
    assert create_res.status_code == 201
    repo_id = create_res.json()["id"]

    # 2. Ingest engineering documents
    docs_payload = {
        "README.md": """# Engineering App
Overview of engineering app.

## Security Rules
- All incoming requests MUST be authenticated.
- Never store plaintext passwords.
""",
        "docs/adr/0001-fastapi.md": """# 0001: Use FastAPI Framework

## Status
Accepted

## Deciders
Architecture Council

## Decision
We MUST use FastAPI for high performance asynchronous web services.
""",
        "docs/guidelines.md": """# Guidelines
- Unit tests SHOULD be runnable in isolation.
""",
    }

    ingest_res = await client.post(
        f"/api/v1/repositories/{repo_id}/engineering/ingest",
        json={"files": docs_payload},
    )
    assert ingest_res.status_code == 201
    ingest_data = ingest_res.json()
    assert ingest_data["indexed_doc_count"] == 3
    assert ingest_data["total_constraints_count"] >= 3

    # 3. Test overview endpoint
    overview_res = await client.get(f"/api/v1/repositories/{repo_id}/engineering/overview")
    assert overview_res.status_code == 200
    overview_data = overview_res.json()
    assert overview_data["total_docs"] == 3
    assert overview_data["total_adrs"] == 1
    assert len(overview_data["adrs"]) == 1
    assert overview_data["adrs"][0]["status"] == "accepted"
    assert len(overview_data["top_constraints"]) >= 3

    # 4. Test list docs
    docs_res = await client.get(f"/api/v1/repositories/{repo_id}/engineering/docs")
    assert docs_res.status_code == 200
    docs_list = docs_res.json()
    assert len(docs_list) == 3

    # Filter docs by doc_type
    adr_docs_res = await client.get(f"/api/v1/repositories/{repo_id}/engineering/docs?doc_type=adr")
    assert adr_docs_res.status_code == 200
    assert len(adr_docs_res.json()) == 1

    # 5. Test doc detail
    doc_id = docs_list[0]["id"]
    detail_res = await client.get(f"/api/v1/repositories/{repo_id}/engineering/docs/{doc_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert "raw_content" in detail_data
    assert "constraints" in detail_data

    # 6. Test ADRs endpoint
    adrs_res = await client.get(
        f"/api/v1/repositories/{repo_id}/engineering/adrs?adr_status=accepted"
    )
    assert adrs_res.status_code == 200
    assert len(adrs_res.json()) == 1

    # 7. Test constraints endpoint
    constraints_res = await client.get(f"/api/v1/repositories/{repo_id}/engineering/constraints")
    assert constraints_res.status_code == 200
    all_c = constraints_res.json()
    assert len(all_c) >= 3

    # Filter constraints by category
    sec_c_res = await client.get(
        f"/api/v1/repositories/{repo_id}/engineering/constraints?category=security"
    )
    assert sec_c_res.status_code == 200
    assert len(sec_c_res.json()) >= 2

    # 8. Test search endpoint
    search_res = await client.get(f"/api/v1/repositories/{repo_id}/engineering/search?q=FastAPI")
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total_matches"] > 0
    assert len(search_data["docs"]) > 0 or len(search_data["constraints"]) > 0
