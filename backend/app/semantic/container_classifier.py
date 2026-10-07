"""C4 Container Boundary & Deployable Unit Classifier.

Classifies software directories, packages, and deployable units into C4 container roles
(api, web_app, worker, database, shared_library, cli_tool) using typed System One
decision models with calibrated fallback heuristics.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from app.semantic.client import SystemOneClient
from app.semantic.systemone import (
    ChoiceAnswer,
    ChoiceQuestion,
    SystemOneQuestion,
    SystemOneRequest,
)

logger = logging.getLogger(__name__)


class ContainerRole(str, Enum):
    """Architectural role of a deployable unit or container."""

    API = "api"
    WEB_APP = "web_app"
    WORKER = "worker"
    DATABASE = "database"
    SHARED_LIBRARY = "shared_library"
    CLI_TOOL = "cli_tool"


CONTAINER_ROLE_OPTIONS: List[str] = [role.value for role in ContainerRole]


@dataclass(frozen=True)
class ContainerClassificationResult:
    """Consolidated classification result for a container/deployable unit."""

    role: ContainerRole
    confidence: float = 1.0
    source: str = "heuristic"  # "model" or "heuristic"
    raw_answer: Optional[str] = None
    fallback_reason: Optional[str] = None


class ContainerClassifier:
    """Classifies container boundaries and deployable unit roles using System One with heuristic fallback."""

    def __init__(self, client: Optional[SystemOneClient] = None) -> None:
        self.client = client or SystemOneClient()

    @staticmethod
    def heuristic_classify(
        path: str,
        files: Optional[Sequence[str]] = None,
        manifest_content: Optional[str] = None,
    ) -> ContainerRole:
        """Deterministic heuristic rule fallback for classifying container role."""
        path_norm = path.lower().replace("\\", "/").strip("/")
        parts = [p.lower() for p in Path(path_norm).parts]
        file_list = [f.lower().replace("\\", "/") for f in (files or [])]
        file_names = {Path(f).name.lower() for f in file_list}
        manifest_lower = (manifest_content or "").lower()

        # 1. Database container check
        if any(p in parts for p in ["db", "database", "postgres", "mysql", "migrations"]) or any(
            fn in file_names for fn in ["schema.sql", "schema.prisma"]
        ):
            # Only classify as database if primarily data/migrations or explicitly named
            if any(p in ["db", "database", "migrations"] for p in parts) or all(
                f.endswith((".sql", ".prisma")) or "migration" in f for f in file_list if f
            ):
                return ContainerRole.DATABASE

        # 2. Worker / Asynchronous Queue Consumer check
        worker_keywords = {"worker", "consumer", "celery", "jobs", "queue", "scheduler", "tasks"}
        has_worker_dir = bool(set(parts) & worker_keywords)
        has_worker_file = any(
            any(k in fn for k in ["worker", "consumer", "celery", "tasks.py", "job.py"])
            for fn in file_names
        )
        has_worker_manifest = any(
            k in manifest_lower for k in ["celery", "bullmq", "dramatiq", "kafkajs", "amqplib"]
        ) and any(k in manifest_lower for k in ["worker", "consume", "process_queue"])

        if has_worker_dir or (
            has_worker_file and not any(k in parts for k in ["web", "ui", "frontend"])
        ):
            return ContainerRole.WORKER
        if has_worker_manifest:
            return ContainerRole.WORKER

        # 3. CLI tool / Command-line executable check
        cli_keywords = {"cli", "cmd", "bin", "tools", "command"}
        has_cli_dir = (
            bool(set(parts) & cli_keywords)
            or any(
                p.startswith(("cmd-", "cmd_"))
                or p.endswith(("-cli", "_cli"))
                or "cli" in p.split("-")
                or "cli" in p.split("_")
                for p in parts
            )
            or any("cmd/" in f or "/cmd/" in f or "cli/" in f for f in file_list)
        )
        has_cli_file = any(
            fn in ["cli.py", "main.go", "cli.ts", "cli.js", "main.rs"]
            or fn.startswith("cli_")
            or fn.startswith("cli-")
            for fn in file_names
        ) and (has_cli_dir or any(p in parts for p in ["cmd", "cli", "bin", "tools"]))
        has_cli_manifest = (
            '"bin":' in manifest_lower
            or "[project.scripts]" in manifest_lower
            or any(
                k in manifest_lower
                for k in ["typer", "click", "argparse", "commander", "yargs", "cobra"]
            )
        )

        if has_cli_dir and (has_cli_file or has_cli_manifest):
            return ContainerRole.CLI_TOOL
        if any(
            p in ["cmd", "cli"] or "cli" in p.split("_") or "cli" in p.split("-") for p in parts
        ) and not any(k in parts for k in ["api", "server", "web"]):
            return ContainerRole.CLI_TOOL

        # 4. Web Application / Frontend UI check
        web_keywords = {"frontend", "client", "web", "ui", "dashboard", "portal"}
        has_web_dir = bool(set(parts) & web_keywords)
        frontend_configs = {
            "next.config.js",
            "next.config.mjs",
            "next.config.ts",
            "vite.config.js",
            "vite.config.ts",
            "nuxt.config.ts",
            "remix.config.js",
            "astro.config.mjs",
            "tailwind.config.js",
            "tailwind.config.ts",
        }
        has_web_config = bool(file_names & frontend_configs) or "index.html" in file_names
        has_web_files = any(
            f.endswith((".tsx", ".jsx", ".vue", ".svelte"))
            or "app/page." in f
            or "app/layout." in f
            for f in file_list
        )
        has_web_manifest = any(
            k in manifest_lower
            for k in ["next", "react-dom", "vue", "svelte", "solid-js", "@angular/core"]
        )

        if (
            has_web_dir
            or has_web_config
            or (has_web_files and not any(k in parts for k in ["backend", "server"]))
        ) and not any(k in parts for k in ["backend", "server", "api"]):
            return ContainerRole.WEB_APP
        if has_web_config or has_web_manifest:
            if not any(k in parts for k in ["backend", "server", "api"]):
                return ContainerRole.WEB_APP

        # 5. Shared Library / Package / Contract check
        library_keywords = {
            "packages",
            "libs",
            "shared",
            "contracts",
            "common",
            "core",
            "sdk",
            "types",
        }
        has_lib_dir = bool(set(parts) & library_keywords)
        is_library_manifest = (
            '"types":' in manifest_lower
            or '"typings":' in manifest_lower
            or ("contracts" in path_norm and '"name":' in manifest_lower)
        ) and not any(
            k in manifest_lower for k in ["fastapi", "express", "next", "react-dom", "start"]
        )

        if has_lib_dir and (
            is_library_manifest
            or not any(
                k in file_names
                for k in ["server.py", "main.py", "app.py", "server.ts", "index.html"]
            )
        ):
            return ContainerRole.SHARED_LIBRARY

        # 6. API / Server / Backend check
        api_keywords = {"backend", "server", "api", "services", "gateway", "microservice"}
        has_api_dir = bool(set(parts) & api_keywords)
        has_api_files = any(
            any(
                k in fn
                for k in [
                    "main.py",
                    "app.py",
                    "server.py",
                    "server.ts",
                    "app.ts",
                    "routes",
                    "controller",
                ]
            )
            for fn in file_names
        )
        has_api_manifest = any(
            k in manifest_lower
            for k in [
                "fastapi",
                "express",
                "flask",
                "django",
                "starlette",
                "uvicorn",
                "gunicorn",
                "nest",
                "spring-boot",
                "gin-gonic",
                "actix-web",
            ]
        )

        if has_api_dir or has_api_files or has_api_manifest:
            return ContainerRole.API

        # Default fallback: if under packages/ or libs/ -> shared_library, else api
        if has_lib_dir:
            return ContainerRole.SHARED_LIBRARY

        return ContainerRole.API

    async def classify_container(
        self,
        path: str,
        files: Optional[Sequence[str]] = None,
        manifest_content: Optional[str] = None,
    ) -> ContainerClassificationResult:
        """Classify a single container using System One with heuristic fallback."""
        file_list = list(files or [])
        sample_files = file_list[:25]
        manifest_snippet = (manifest_content or "")[:1500] if manifest_content else ""

        state: Dict[str, Any] = {
            "directory": path,
            "representative_files": sample_files,
            "file_count": len(file_list),
            "manifest_snippet": manifest_snippet,
        }

        question = ChoiceQuestion(
            instructions=(
                "Classify the architectural role of this software container or deployable unit. "
                "Choose 'api' for backend servers and REST/gRPC endpoints, "
                "'web_app' for frontend user interfaces and single-page apps, "
                "'worker' for background job processors and async queue consumers, "
                "'database' for persistent storage engines and schema migrations, "
                "'shared_library' for reusable packages, SDKs, and contracts, "
                "or 'cli_tool' for command-line utilities and developer tools."
            ),
            options=CONTAINER_ROLE_OPTIONS,
        )

        heuristic_role = self.heuristic_classify(path, file_list, manifest_content)

        if not self.client.enabled:
            return ContainerClassificationResult(
                role=heuristic_role,
                confidence=1.0,
                source="heuristic",
                fallback_reason="client_disabled",
            )

        try:
            request = SystemOneRequest(
                model=self.client.model,
                state=state,
                questions={"container_role": question},
            )
            response = await self.client.ask(request)
            answer_obj = response.answers.get("container_role")

            if answer_obj and isinstance(answer_obj, ChoiceAnswer):
                prob = answer_obj.probabilities.get(answer_obj.choice, answer_obj.confidence)
                if prob >= self.client.confidence_threshold:
                    try:
                        role_enum = ContainerRole(answer_obj.choice)
                        return ContainerClassificationResult(
                            role=role_enum,
                            confidence=prob,
                            source="model",
                            raw_answer=answer_obj.choice,
                        )
                    except ValueError:
                        pass
                return ContainerClassificationResult(
                    role=heuristic_role,
                    confidence=prob,
                    source="heuristic",
                    raw_answer=answer_obj.choice,
                    fallback_reason=f"low_confidence_{prob:.2f}",
                )

            return ContainerClassificationResult(
                role=heuristic_role,
                confidence=1.0,
                source="heuristic",
                fallback_reason="missing_answer",
            )

        except Exception as exc:
            logger.warning(
                "SystemOne container classification failed for %s: %s; falling back to heuristic",
                path,
                exc,
            )
            return ContainerClassificationResult(
                role=heuristic_role,
                confidence=1.0,
                source="heuristic",
                fallback_reason=f"exception_{type(exc).__name__}",
            )

    async def classify_containers_batch(
        self,
        containers: Sequence[Dict[str, Any]],
    ) -> Dict[str, ContainerClassificationResult]:
        """Batch classify multiple containers.

        Each item in `containers` should have:
        - `path`: str (directory path identifier)
        - `files`: Optional[Sequence[str]]
        - `manifest_content`: Optional[str]
        """
        results: Dict[str, ContainerClassificationResult] = {}
        if not containers:
            return results

        if not self.client.enabled:
            for item in containers:
                path = item.get("path", "")
                files = item.get("files", [])
                manifest = item.get("manifest_content")
                results[path] = ContainerClassificationResult(
                    role=self.heuristic_classify(path, files, manifest),
                    confidence=1.0,
                    source="heuristic",
                    fallback_reason="client_disabled",
                )
            return results

        # Construct batch request
        questions: Dict[str, SystemOneQuestion] = {}
        heuristic_by_id: Dict[str, ContainerRole] = {}

        for idx, item in enumerate(containers):
            q_id = f"cont_{idx}"
            path = item.get("path", "")
            files = item.get("files", [])
            manifest = item.get("manifest_content")
            heuristic_by_id[q_id] = self.heuristic_classify(path, files, manifest)

            questions[q_id] = ChoiceQuestion(
                instructions=(
                    "Classify the architectural role of this container/directory: "
                    f"path='{path}'. Choose one of: api, web_app, worker, database, shared_library, cli_tool."
                ),
                options=CONTAINER_ROLE_OPTIONS,
            )

        batch_state = {
            "containers": [
                {
                    "id": f"cont_{idx}",
                    "path": item.get("path", ""),
                    "files": list(item.get("files", []))[:15],
                    "manifest_snippet": (item.get("manifest_content") or "")[:500],
                }
                for idx, item in enumerate(containers)
            ]
        }

        try:
            request = SystemOneRequest(
                model=self.client.model,
                state=batch_state,
                questions=questions,
            )
            response = await self.client.ask(request)

            for idx, item in enumerate(containers):
                q_id = f"cont_{idx}"
                path = item.get("path", "")
                answer_obj = response.answers.get(q_id)
                heuristic_role = heuristic_by_id[q_id]

                if answer_obj and isinstance(answer_obj, ChoiceAnswer):
                    prob = answer_obj.probabilities.get(answer_obj.choice, answer_obj.confidence)
                    if prob >= self.client.confidence_threshold:
                        try:
                            role_enum = ContainerRole(answer_obj.choice)
                            results[path] = ContainerClassificationResult(
                                role=role_enum,
                                confidence=prob,
                                source="model",
                                raw_answer=answer_obj.choice,
                            )
                            continue
                        except ValueError:
                            pass
                    results[path] = ContainerClassificationResult(
                        role=heuristic_role,
                        confidence=prob,
                        source="heuristic",
                        raw_answer=answer_obj.choice,
                        fallback_reason=f"low_confidence_{prob:.2f}",
                    )
                else:
                    results[path] = ContainerClassificationResult(
                        role=heuristic_role,
                        confidence=1.0,
                        source="heuristic",
                        fallback_reason="missing_answer",
                    )
        except Exception as exc:
            logger.warning(
                "Batch container classification failed: %s; falling back to heuristic",
                exc,
            )
            for idx, item in enumerate(containers):
                q_id = f"cont_{idx}"
                path = item.get("path", "")
                results[path] = ContainerClassificationResult(
                    role=heuristic_by_id[q_id],
                    confidence=1.0,
                    source="heuristic",
                    fallback_reason=f"exception_{type(exc).__name__}",
                )

        return results
