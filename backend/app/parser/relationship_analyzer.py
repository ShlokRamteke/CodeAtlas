from __future__ import annotations

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
                    target_path = dep.target_path
                    relationships.append(
                        RelationshipEdge(
                            source_name=p.stem,
                            source_path=f.path,
                            target_name=Path(target_path).stem,
                            target_path=target_path,
                            type="imports",
                        )
                    )
                    if target_path not in comp.dependencies:
                        comp.dependencies.append(target_path)

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
