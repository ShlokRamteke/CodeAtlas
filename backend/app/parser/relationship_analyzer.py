from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from app.parser.ast_parser import ParsedFileResult


@dataclass
class ComponentInfo:
    name: str
    path: str
    symbol_count: int = 0
    file_count: int = 0
    dependencies: List[str] = field(default_factory=list)
    tested_by: Optional[str] = None


@dataclass
class RelationshipEdge:
    source_name: str
    source_path: str
    target_name: str
    target_path: str
    type: str  # imports, calls, extends, implements, tested_by
    confidence: float = 1.0
    resolution_method: str = "tree_sitter_ast"


@dataclass
class ArchitectureGraph:
    file_count: int
    symbol_count: int
    dependency_count: int
    languages: Dict[str, int]
    major_components: List[ComponentInfo]
    relationships: List[RelationshipEdge]


class RelationshipAnalyzer:
    """Analyzes architecture relationships, component boundaries, and test linkages."""

    @staticmethod
    def is_test_file(path: str) -> bool:
        p = path.lower()
        return (
            ".test." in p
            or ".spec." in p
            or "/tests/" in p
            or "/__tests__/" in p
            or p.startswith("test_")
            or "/test_" in p
        )

    @staticmethod
    def find_target_for_test(test_path: str, all_paths: List[str]) -> Optional[str]:
        """Given a test file path, find the source file it tests."""
        test_file = Path(test_path)
        stem = test_file.name

        # Handle prefixes / suffixes:
        # e.g. PaymentService.test.ts -> PaymentService
        # e.g. test_payment.py -> payment
        target_name = stem
        for suffix in [".test", ".spec", "_test"]:
            target_name = target_name.replace(suffix, "")
        if target_name.startswith("test_"):
            target_name = target_name[5:]

        target_stem = Path(target_name).stem.lower()

        # Check exact filename match in same or parent directory
        for p in all_paths:
            if p == test_path or RelationshipAnalyzer.is_test_file(p):
                continue
            cand_stem = Path(p).stem.lower()
            if cand_stem == target_stem:
                return p

        return None

    @staticmethod
    def resolve_import_path(
        source_path: str,
        target_import: str,
        all_paths: List[str],
    ) -> str:
        """Resolve an import path (relative, alias @/, ~/, or module notation) to a concrete repo file path."""
        if not target_import:
            return target_import

        clean_tgt = target_import.strip()
        all_paths_set = set(all_paths)
        all_paths_lower_map = {p.lower(): p for p in all_paths}

        candidates: List[str] = []

        # 1. Alias handling (@/, ~/, #/, $lib/)
        if clean_tgt.startswith(("@/", "~/", "#/", "$lib/")):
            stripped = clean_tgt.split("/", 1)[1] if "/" in clean_tgt else clean_tgt
            candidates.append(stripped)
            candidates.append(f"src/{stripped}")
            candidates.append(f"app/{stripped}")
            candidates.append(f"frontend/{stripped}")
            candidates.append(f"frontend/src/{stripped}")
            candidates.append(f"client/{stripped}")
            candidates.append(f"client/src/{stripped}")
        # 2. Relative import handling (./, ../)
        elif clean_tgt.startswith("."):
            src_parent = Path(source_path).parent
            try:
                resolved_rel = os.path.normpath(str(src_parent / clean_tgt)).replace("\\", "/")
                candidates.append(resolved_rel)
            except Exception:
                pass
        # 3. Python module style (app.models.user)
        elif "." in clean_tgt and not any(
            clean_tgt.endswith(ext)
            for ext in [".js", ".ts", ".jsx", ".tsx", ".py", ".css", ".json", ".mjs"]
        ):
            py_path = clean_tgt.replace(".", "/")
            candidates.append(py_path)
            candidates.append(f"{py_path}.py")
            candidates.append(f"backend/{py_path}.py")
            candidates.append(f"backend/{py_path}")
        else:
            candidates.append(clean_tgt)
            candidates.append(f"src/{clean_tgt}")
            candidates.append(f"app/{clean_tgt}")

        # Check each candidate against all_paths
        common_exts = [
            "",
            ".tsx",
            ".ts",
            ".jsx",
            ".js",
            ".py",
            ".go",
            ".rs",
            ".vue",
            ".svelte",
            ".mjs",
            ".cjs",
            "/index.tsx",
            "/index.ts",
            "/index.jsx",
            "/index.js",
            "/__init__.py",
        ]
        for cand in candidates:
            cand_norm = cand.replace("\\", "/").lstrip("/")
            for ext in common_exts:
                test_path = f"{cand_norm}{ext}"
                if test_path in all_paths_set:
                    return test_path
                test_lower = test_path.lower()
                if test_lower in all_paths_lower_map:
                    return all_paths_lower_map[test_lower]

        # Suffix matching: e.g. components/dropzone matches convert-zone/components/dropzone.tsx
        for cand in candidates:
            cand_norm = cand.replace("\\", "/").lstrip("/").lower()
            if not cand_norm:
                continue
            for p in all_paths:
                p_lower = p.lower()
                p_without_ext = str(Path(p_lower).with_suffix(""))
                if p_without_ext.endswith(cand_norm) or cand_norm in p_without_ext:
                    return p

        return candidates[0] if candidates else target_import

    def analyze_repository(self, parsed_files: List[ParsedFileResult]) -> ArchitectureGraph:
        all_paths = [f.path for f in parsed_files]
        languages: Dict[str, int] = {}
        total_symbols = 0
        total_dependencies = 0

        # Component map keyed by parent component directory
        component_map: Dict[str, ComponentInfo] = {}
        relationships: List[RelationshipEdge] = []

        # 1. Map test files
        test_links: Dict[str, str] = {}
        for f in parsed_files:
            if self.is_test_file(f.path):
                target = self.find_target_for_test(f.path, all_paths)
                if target:
                    test_links[target] = f.path

        # 2. Process each file
        for f in parsed_files:
            if f.language not in languages:
                languages[f.language] = 0
            languages[f.language] += 1

            sym_count = len(f.symbols)
            total_symbols += sym_count
            dep_count = len(f.dependencies)
            total_dependencies += dep_count

            # Determine logical component directory
            p = Path(f.path)
            parts = p.parts
            if len(parts) > 1:
                comp_dir = "/".join(parts[: min(2, len(parts) - 1)])
            else:
                comp_dir = "root"

            if comp_dir not in component_map:
                component_map[comp_dir] = ComponentInfo(
                    name=comp_dir.replace("/", " > "),
                    path=comp_dir,
                )

            comp = component_map[comp_dir]
            comp.symbol_count += sym_count
            comp.file_count += 1
            if f.path in test_links:
                comp.tested_by = test_links[f.path]

            # Dependencies to relationships
            for dep in f.dependencies:
                if dep.kind in ["internal", "relative"]:
                    # Clean relative import to find candidate target
                    resolved_target = self.resolve_import_path(f.path, dep.target_path, all_paths)
                    is_resolved = resolved_target in all_paths
                    relationships.append(
                        RelationshipEdge(
                            source_name=p.stem,
                            source_path=f.path,
                            target_name=Path(resolved_target).stem,
                            target_path=resolved_target,
                            type="imports",
                            confidence=1.0 if is_resolved else 0.85,
                            resolution_method="ast_import_resolver"
                            if is_resolved
                            else "tree_sitter_ast",
                        )
                    )
                    if resolved_target not in comp.dependencies:
                        comp.dependencies.append(resolved_target)

        # Add tested_by relationships
        for target, test_file in test_links.items():
            relationships.append(
                RelationshipEdge(
                    source_name=Path(target).stem,
                    source_path=target,
                    target_name=Path(test_file).stem,
                    target_path=test_file,
                    type="tested_by",
                    confidence=0.90,
                    resolution_method="filename_heuristic",
                )
            )

        return ArchitectureGraph(
            file_count=len(parsed_files),
            symbol_count=total_symbols,
            dependency_count=total_dependencies,
            languages=languages,
            major_components=list(component_map.values()),
            relationships=relationships,
        )
