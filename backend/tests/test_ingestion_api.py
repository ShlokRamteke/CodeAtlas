from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_repository_ingest_and_query_endpoints(client: AsyncClient) -> None:
    # 1. Create a repository
    create_res = await client.post(
        "/api/v1/repositories",
        json={
            "owner": "test-org",
            "name": "payments-app",
            "full_name": "test-org/payments-app",
            "default_branch": "main",
        },
    )
    assert create_res.status_code == 201
    repo_data = create_res.json()
    repo_id = repo_data["id"]

    # 2. Ingest sample files
    sample_files = {
        "src/models/Payment.ts": """
        export interface Payment {
            id: string;
            amount: number;
            currency: string;
        }
        """,
        "src/services/PaymentService.ts": """
        import { Payment } from '../models/Payment';
        import axios from 'axios';

        export class PaymentService {
            processPayment(payment: Payment): boolean {
                return true;
            }
        }
        """,
        "src/services/PaymentService.test.ts": """
        import { PaymentService } from './PaymentService';

        export const runTests = () => {
            const service = new PaymentService();
            return service.processPayment({ id: '1', amount: 100, currency: 'USD' });
        };
        """,
    }

    ingest_res = await client.post(
        f"/api/v1/repositories/{repo_id}/ingest",
        json={"files": sample_files},
    )
    assert ingest_res.status_code == 200
    arch_data = ingest_res.json()
    assert arch_data["file_count"] == 3
    assert arch_data["symbol_count"] >= 3
    assert arch_data["dependency_count"] >= 3

    # 3. Query symbols
    symbols_res = await client.get(f"/api/v1/repositories/{repo_id}/symbols")
    assert symbols_res.status_code == 200
    symbols = symbols_res.json()
    assert len(symbols) >= 3
    symbol_names = [s["name"] for s in symbols]
    assert "Payment" in symbol_names
    assert "PaymentService" in symbol_names

    # Filter symbols by name and kind
    filtered_symbols_res = await client.get(
        f"/api/v1/repositories/{repo_id}/symbols?name=PaymentService&kind=class"
    )
    assert filtered_symbols_res.status_code == 200
    filtered = filtered_symbols_res.json()
    assert len(filtered) == 1
    assert filtered[0]["name"] == "PaymentService"
    assert filtered[0]["kind"] == "class"


    # 4. Query dependencies
    deps_res = await client.get(f"/api/v1/repositories/{repo_id}/dependencies")
    assert deps_res.status_code == 200
    deps = deps_res.json()
    assert len(deps) >= 3

    # 5. Query architecture overview
    arch_res = await client.get(f"/api/v1/repositories/{repo_id}/architecture")
    assert arch_res.status_code == 200
    arch = arch_res.json()
    assert arch["file_count"] == 3
    assert len(arch["major_components"]) >= 1
    assert len(arch["relationships"]) >= 1
