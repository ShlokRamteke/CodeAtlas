"""Unit Tests for C4 Container Boundary & Deployable Unit Classifier."""

from __future__ import annotations

import pytest

from app.semantic.client import MockSystemOneClient
from app.semantic.container_classifier import (
    ContainerClassifier,
    ContainerRole,
)


def test_heuristic_classify_web_apps():
    """Verify web application directories, files, and manifests classify as WEB_APP."""
    # Frontend directory with TSX
    role = ContainerClassifier.heuristic_classify(
        path="frontend",
        files=["frontend/src/app/page.tsx", "frontend/src/app/layout.tsx"],
    )
    assert role == ContainerRole.WEB_APP

    # Next.js config
    role = ContainerClassifier.heuristic_classify(
        path="client",
        files=["client/next.config.js", "client/src/index.js"],
    )
    assert role == ContainerRole.WEB_APP

    # Vite app
    role = ContainerClassifier.heuristic_classify(
        path="apps/web",
        files=["apps/web/vite.config.ts", "apps/web/index.html"],
        manifest_content='{"dependencies": {"react": "^18.0.0", "react-dom": "^18.0.0"}}',
    )
    assert role == ContainerRole.WEB_APP


def test_heuristic_classify_api():
    """Verify backend API directories, files, and manifests classify as API."""
    role = ContainerClassifier.heuristic_classify(
        path="backend",
        files=["backend/app/main.py", "backend/app/api/endpoints.py"],
        manifest_content="[project.dependencies]\nfastapi = '>=0.100.0'\nuvicorn = '>=0.20.0'",
    )
    assert role == ContainerRole.API

    role = ContainerClassifier.heuristic_classify(
        path="services/auth",
        files=["services/auth/server.ts", "services/auth/routes.ts"],
        manifest_content='{"dependencies": {"express": "^4.18.2"}}',
    )
    assert role == ContainerRole.API


def test_heuristic_classify_worker():
    """Verify background worker directories and consumer jobs classify as WORKER."""
    role = ContainerClassifier.heuristic_classify(
        path="services/worker",
        files=["services/worker/tasks.py", "services/worker/celery_app.py"],
        manifest_content="celery = '>=5.3.0'",
    )
    assert role == ContainerRole.WORKER

    role = ContainerClassifier.heuristic_classify(
        path="apps/job-runner",
        files=["apps/job-runner/consumer.ts", "apps/job-runner/queue.ts"],
        manifest_content='{"dependencies": {"bullmq": "^4.0.0"}}',
    )
    assert role == ContainerRole.WORKER


def test_heuristic_classify_cli():
    """Verify CLI tools and command utilities classify as CLI_TOOL."""
    role = ContainerClassifier.heuristic_classify(
        path="cmd/cli",
        files=["cmd/cli/main.go", "cmd/cli/root.go"],
    )
    assert role == ContainerRole.CLI_TOOL

    role = ContainerClassifier.heuristic_classify(
        path="tools/indexer-cli",
        files=["tools/indexer-cli/cli.py"],
        manifest_content="[project.scripts]\nindexer = 'cli:main'",
    )
    assert role == ContainerRole.CLI_TOOL


def test_heuristic_classify_shared_library():
    """Verify shared packages, contracts, and SDKs classify as SHARED_LIBRARY."""
    role = ContainerClassifier.heuristic_classify(
        path="packages/contracts",
        files=["packages/contracts/src/types.ts", "packages/contracts/src/index.ts"],
        manifest_content='{"name": "@app/contracts", "types": "dist/index.d.ts"}',
    )
    assert role == ContainerRole.SHARED_LIBRARY

    role = ContainerClassifier.heuristic_classify(
        path="libs/common",
        files=["libs/common/utils.py", "libs/common/__init__.py"],
    )
    assert role == ContainerRole.SHARED_LIBRARY


def test_heuristic_classify_database():
    """Verify database and migrations directories classify as DATABASE."""
    role = ContainerClassifier.heuristic_classify(
        path="db",
        files=["db/schema.sql", "db/seeds.sql"],
    )
    assert role == ContainerRole.DATABASE

    role = ContainerClassifier.heuristic_classify(
        path="database/migrations",
        files=["database/migrations/001_initial.sql"],
    )
    assert role == ContainerRole.DATABASE


@pytest.mark.asyncio
async def test_classify_container_disabled_client():
    """Verify classifier uses heuristic fallback when client is disabled."""
    client = MockSystemOneClient(enabled=False)
    classifier = ContainerClassifier(client=client)

    result = await classifier.classify_container(
        path="frontend",
        files=["frontend/src/app/page.tsx"],
    )
    assert result.role == ContainerRole.WEB_APP
    assert result.source == "heuristic"
    assert result.fallback_reason == "client_disabled"


@pytest.mark.asyncio
async def test_classify_container_model_high_confidence():
    """Verify classifier accepts high-confidence System One model output."""
    client = MockSystemOneClient(enabled=True)
    client.set_choice_response("container_role", "worker", confidence=0.95)
    classifier = ContainerClassifier(client=client)

    result = await classifier.classify_container(
        path="services/event-consumer",
        files=["services/event-consumer/main.py"],
    )
    assert result.role == ContainerRole.WORKER
    assert result.source == "model"
    assert result.confidence == 0.95
    assert result.raw_answer == "worker"


@pytest.mark.asyncio
async def test_classify_container_model_low_confidence_fallback():
    """Verify classifier falls back to heuristic when model confidence < 0.85."""
    client = MockSystemOneClient(enabled=True, confidence_threshold=0.85)
    client.set_choice_response("container_role", "api", confidence=0.60)
    classifier = ContainerClassifier(client=client)

    result = await classifier.classify_container(
        path="services/worker",
        files=["services/worker/tasks.py"],
    )
    # Heuristic identifies "worker" from path
    assert result.role == ContainerRole.WORKER
    assert result.source == "heuristic"
    assert "low_confidence" in (result.fallback_reason or "")


@pytest.mark.asyncio
async def test_classify_container_model_exception_fallback():
    """Verify classifier falls back gracefully on client error."""
    client = MockSystemOneClient(enabled=True)

    async def raise_error(*args, **kwargs):
        raise ConnectionError("Connection refused to /v1/systemone")

    client.ask = raise_error  # type: ignore

    classifier = ContainerClassifier(client=client)
    result = await classifier.classify_container(
        path="cmd/ctl",
        files=["cmd/ctl/main.go"],
    )
    assert result.role == ContainerRole.CLI_TOOL
    assert result.source == "heuristic"
    assert "exception" in (result.fallback_reason or "")


@pytest.mark.asyncio
async def test_classify_containers_batch():
    """Verify batch container classification across heterogeneous packages."""
    client = MockSystemOneClient(enabled=False)
    classifier = ContainerClassifier(client=client)

    containers = [
        {"path": "frontend", "files": ["frontend/src/app/page.tsx"]},
        {"path": "backend", "files": ["backend/app/main.py"]},
        {"path": "packages/contracts", "files": ["packages/contracts/src/types.ts"]},
        {"path": "services/queue-worker", "files": ["services/queue-worker/worker.py"]},
        {"path": "cmd/atlas-cli", "files": ["cmd/atlas-cli/main.go"]},
    ]

    results = await classifier.classify_containers_batch(containers)

    assert results["frontend"].role == ContainerRole.WEB_APP
    assert results["backend"].role == ContainerRole.API
    assert results["packages/contracts"].role == ContainerRole.SHARED_LIBRARY
    assert results["services/queue-worker"].role == ContainerRole.WORKER
    assert results["cmd/atlas-cli"].role == ContainerRole.CLI_TOOL
