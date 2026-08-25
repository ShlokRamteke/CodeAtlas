from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from app.context_builder.project_context import (
    ContextEntity,
    ContextEvidence,
    ContextRelationship,
    ContextUnknown,
    ProjectContext,
)


class CurrentSystemContextBuilder:
    """
    Constructs one canonical ProjectContext shared by the human UI and AI/agent workflows.
    Ensures zero separate knowledge pipelines.
    """

    def build_project_context(
        self,
        target_id: str,
        target_name: str,
        target_type: str,  # repository, component, file
        files: List[dict],
        symbols: List[dict],
        dependencies: List[dict],
        relationships: List[dict],
        component_filter: Optional[str] = None,
    ) -> ProjectContext:
        # 1. Filter files if scoped to a specific component or path
        if component_filter:
            target_files = [
                f for f in files
                if f.get("path", "").startswith(component_filter)
                or Path(f.get("path", "")).stem.lower() == component_filter.lower()
            ]
            if not target_files and files:
                target_files = files
        else:
            target_files = files

        target_file_ids = {f.get("id") for f in target_files if f.get("id")}
        target_file_paths = {f.get("path") for f in target_files if f.get("path")}

        # 2. Build Entities
        entities: List[ContextEntity] = []

        # Add File Entities
        for f in target_files:
            entities.append(
                ContextEntity(
                    id=str(f.get("id") or uuid.uuid4()),
                    name=Path(f.get("path", "")).name,
                    kind="file",
                    path=f.get("path", ""),
                    language=f.get("language"),
                )
            )

        # Add Symbol Entities
        target_symbols = [s for s in symbols if not target_file_ids or s.get("file_id") in target_file_ids]
        for s in target_symbols:
            entities.append(
                ContextEntity(
                    id=str(s.get("id") or uuid.uuid4()),
                    name=s.get("name", ""),
                    kind="symbol",
                    path=s.get("path") or "",
                    signature=s.get("signature"),
                    line_start=s.get("line_start"),
                    line_end=s.get("line_end"),
                )
            )

        # 3. Build Canonical Relationships
        context_relationships: List[ContextRelationship] = []
        for r in relationships:
            src_path = r.get("source_path", "")
            tgt_path = r.get("target_path", "")
            if not component_filter or src_path in target_file_paths or tgt_path in target_file_paths:
                context_relationships.append(
                    ContextRelationship(
                        source_name=r.get("source_name", ""),
                        source_path=src_path,
                        target_name=r.get("target_name", ""),
                        target_path=tgt_path,
                        type=r.get("type", "imports"),
                        confidence=float(r.get("confidence", 1.0)),
                        resolution_method=r.get("resolution_method", "tree_sitter_ast"),
                    )
                )

        # 4. Build Evidence Records
        evidence: List[ContextEvidence] = []
        for s in target_symbols[:20]:
            evidence.append(
                ContextEvidence(
                    id=str(uuid.uuid4()),
                    source_path=s.get("path") or target_name,
                    kind="ast_symbol",
                    content=f"{s.get('kind', 'symbol')} {s.get('name')}: {s.get('signature', '')}",
                    confidence=1.0,
                    provenance="tree_sitter_ast",
                )
            )

        for d in dependencies:
            if not target_file_ids or d.get("source_file_id") in target_file_ids:
                evidence.append(
                    ContextEvidence(
                        id=str(uuid.uuid4()),
                        source_path=d.get("source_path", target_name),
                        kind="import_statement",
                        content=f"import {d.get('imported_symbol') or '*'} from '{d.get('target_path')}'",
                        confidence=float(d.get("confidence", 1.0)),
                        provenance="tree_sitter_ast",
                    )
                )

        for r in context_relationships:
            if r.type == "tested_by":
                evidence.append(
                    ContextEvidence(
                        id=str(uuid.uuid4()),
                        source_path=r.source_path,
                        kind="test_binding",
                        content=f"{r.source_name} verified by test file {r.target_path}",
                        confidence=r.confidence,
                        provenance=r.resolution_method,
                    )
                )

        # 5. Detect Unknowns & Uncertainties
        unknowns: List[ContextUnknown] = []

        # Check for untested source files
        tested_sources = {r.source_path for r in context_relationships if r.type == "tested_by"}
        for f in target_files:
            p = f.get("path", "")
            if not self._is_test_path(p) and p not in tested_sources:
                unknowns.append(
                    ContextUnknown(
                        kind="untested",
                        target=p,
                        description=f"No associated unit or integration test suite linked to '{p}'.",
                        severity="medium",
                    )
                )

        # Check for unresolved external dependencies
        for d in dependencies:
            if not target_file_ids or d.get("source_file_id") in target_file_ids:
                if d.get("kind") == "external":
                    unknowns.append(
                        ContextUnknown(
                            kind="unresolved_dependency",
                            target=d.get("target_path", "external_package"),
                            description=f"External package '{d.get('target_path')}' imported without local source inspection.",
                            severity="low",
                        )
                    )

        # Check for empty files (no AST symbols extracted)
        symbol_file_ids = {s.get("file_id") for s in symbols if s.get("file_id")}
        for f in target_files:
            if f.get("id") and f.get("id") not in symbol_file_ids and not self._is_test_path(f.get("path", "")):
                unknowns.append(
                    ContextUnknown(
                        kind="empty_file",
                        target=f.get("path", ""),
                        description=f"No structural AST symbols were extracted from '{f.get('path')}'.",
                        severity="low",
                    )
                )

        # Check for heuristic/low-confidence relationships
        for r in context_relationships:
            if r.confidence < 1.0:
                unknowns.append(
                    ContextUnknown(
                        kind="low_confidence",
                        target=f"{r.source_name} -> {r.target_name}",
                        description=f"Relationship '{r.type}' inferred via {r.resolution_method} with {int(r.confidence * 100)}% confidence.",
                        severity="low",
                    )
                )

        # 6. Overall Confidence Calculation
        if context_relationships:
            avg_rel_conf = sum(r.confidence for r in context_relationships) / len(context_relationships)
        else:
            avg_rel_conf = 1.0
        overall_confidence = round(avg_rel_conf, 2)

        # 7. Summary
        if component_filter:
            summary = f"Deterministic current-system model for component '{component_filter}' with {len(target_symbols)} symbols and {len(context_relationships)} relationships."
        else:
            summary = f"Deterministic current-system model for repository '{target_name}' across {len(target_files)} files, {len(target_symbols)} symbols, and {len(context_relationships)} relationship edges."

        return ProjectContext(
            target_type=target_type,
            target_id=target_id,
            target_name=target_name,
            summary=summary,
            entities=entities,
            relationships=context_relationships,
            evidence=evidence,
            unknowns=unknowns,
            confidence=overall_confidence,
            provenance="tree_sitter_ast",
        )

    def build_component_brief(
        self,
        component_path: str,
        files: List[dict],
        symbols: List[dict],
        dependencies: List[dict],
        relationships: List[dict],
    ) -> ComponentBrief:
        """Convenience wrapper for component-level briefing."""
        ctx = self.build_project_context(
            target_id=component_path,
            target_name=component_path,
            target_type="component",
            files=files,
            symbols=symbols,
            dependencies=dependencies,
            relationships=relationships,
            component_filter=component_path,
        )

        sym_entities = [e for e in ctx.entities if e.kind == "symbol"]
        callers = [
            {"caller": r.source_name, "path": r.source_path, "type": r.type}
            for r in ctx.relationships
            if r.type in ["imports", "calls"]
        ]
        tests = [r.target_path for r in ctx.relationships if r.type == "tested_by"]

        return ComponentBrief(
            name=component_path,
            path=component_path,
            language="typescript",
            symbol_count=len(sym_entities),
            symbols=[{"name": s.name, "kind": s.kind, "signature": s.signature or ""} for s in sym_entities],
            dependencies=[
                {"target": r.target_path, "symbol": r.target_name, "kind": "internal", "confidence": str(r.confidence)}
                for r in ctx.relationships
                if r.type == "imports"
            ],
            callers=callers,
            tests=tests,
            human_summary=ctx.to_human_markdown(),
            llm_context=ctx.to_llm_prompt(),
        )

    @staticmethod
    def _is_test_path(path: str) -> bool:
        p = path.lower()
        return (
            ".test." in p
            or ".spec." in p
            or "/tests/" in p
            or "/__tests__/" in p
            or p.startswith("test_")
            or "/test_" in p
        )


@dataclass
class ComponentBrief:
    name: str
    path: str
    language: str
    symbol_count: int
    symbols: List[Dict[str, str]]
    dependencies: List[Dict[str, str]]
    callers: List[Dict[str, str]]
    tests: List[str]
    human_summary: str
    llm_context: str

