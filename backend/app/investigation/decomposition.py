from __future__ import annotations

import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


def _normalize_path(path: str) -> str:
    """Normalize file path by removing leading slashes and dot prefixes."""
    p = path.strip()
    if p.startswith("./"):
        p = p[2:]
    return p.lstrip("/")


@dataclass
class ChangeCluster:
    """Represents an independent, weakly-connected cluster of proposed changes."""

    cluster_id: str
    name: str
    dominant_component: str
    files: List[str]
    internal_edge_count: int = 0
    external_dependencies: List[str] = field(default_factory=list)
    suggested_pr_title: str = ""
    suggested_branch_name: str = ""
    rationale: str = ""
    recommended_order: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "name": self.name,
            "dominant_component": self.dominant_component,
            "files": self.files,
            "internal_edge_count": self.internal_edge_count,
            "external_dependencies": self.external_dependencies,
            "suggested_pr_title": self.suggested_pr_title,
            "suggested_branch_name": self.suggested_branch_name,
            "rationale": self.rationale,
            "recommended_order": self.recommended_order,
        }


@dataclass
class ChangeDecompositionReport:
    """Aggregate report evaluating change independence and decomposition into modular PRs."""

    target_files: List[str] = field(default_factory=list)
    total_files: int = 0
    component_count: int = 0
    is_decomposable: bool = False
    modularity_score: float = 0.0
    clusters: List[ChangeCluster] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_files": self.target_files,
            "total_files": self.total_files,
            "component_count": self.component_count,
            "is_decomposable": self.is_decomposable,
            "modularity_score": round(self.modularity_score, 3),
            "clusters": [c.to_dict() for c in self.clusters],
            "summary": self.summary,
        }


class ChangeDecomposer:
    """
    Evaluates weakly-connected components across the dependency subgraph of proposed modified files.
    Suggests splitting large, unrelated change bundles into independent, modular pull requests.
    """

    @staticmethod
    def get_component_name(path: str) -> str:
        """Extract logical component or folder name for a given file path."""
        parts = Path(path).parts
        if len(parts) > 1:
            return "/".join(parts[: min(2, len(parts) - 1)])
        return "root"

    @classmethod
    def evaluate_subgraph(
        cls,
        target_files: List[str],
        dependency_edges: List[Tuple[str, str]],
    ) -> ChangeDecompositionReport:
        """
        Compute weakly-connected components on the induced dependency subgraph of target_files.
        dependency_edges contains (source_path, target_path) where source imports / calls target.
        """
        normalized_targets = [_normalize_path(f) for f in target_files if f.strip()]
        unique_targets = sorted(list(dict.fromkeys(normalized_targets)))

        if not unique_targets:
            return ChangeDecompositionReport(
                target_files=[],
                total_files=0,
                component_count=0,
                is_decomposable=False,
                modularity_score=0.0,
                clusters=[],
                summary="No target files specified for decomposition analysis.",
            )

        if len(unique_targets) == 1:
            single_file = unique_targets[0]
            comp_name = cls.get_component_name(single_file)
            stem = Path(single_file).stem
            cluster = ChangeCluster(
                cluster_id="cluster-1",
                name=f"{comp_name} ({stem})",
                dominant_component=comp_name,
                files=[single_file],
                internal_edge_count=0,
                external_dependencies=[],
                suggested_pr_title=f"feat({comp_name.replace('/', '-') or stem}): update {stem}",
                suggested_branch_name=f"feat/{comp_name.replace('/', '-') or stem}-{stem}".lower(),
                rationale="Single file change; naturally atomic.",
                recommended_order=1,
            )
            return ChangeDecompositionReport(
                target_files=unique_targets,
                total_files=1,
                component_count=1,
                is_decomposable=False,
                modularity_score=0.0,
                clusters=[cluster],
                summary="Proposed change consists of a single file and cannot be further decomposed.",
            )

        target_set: Set[str] = set(unique_targets)

        # 1. Build induced undirected adjacency graph over target_files
        # and record directed edges for topological ordering analysis
        undirected_adj: Dict[str, Set[str]] = defaultdict(set)
        directed_internal: Dict[str, Set[str]] = defaultdict(set)
        external_deps_map: Dict[str, Set[str]] = defaultdict(set)

        for raw_src, raw_tgt in dependency_edges:
            src = _normalize_path(raw_src)
            tgt = _normalize_path(raw_tgt)

            if src in target_set and tgt in target_set and src != tgt:
                undirected_adj[src].add(tgt)
                undirected_adj[tgt].add(src)
                directed_internal[src].add(tgt)
            elif src in target_set and tgt not in target_set:
                external_deps_map[src].add(tgt)

        # 2. Extract Weakly-Connected Components (WCC) via BFS
        visited: Set[str] = set()
        components: List[List[str]] = []

        for node in unique_targets:
            if node not in visited:
                comp_files: List[str] = []
                queue: deque[str] = deque([node])
                visited.add(node)

                while queue:
                    curr = queue.popleft()
                    comp_files.append(curr)
                    for neighbor in sorted(undirected_adj.get(curr, set())):
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)

                components.append(sorted(comp_files))

        # Sort components: larger components first, then by earliest file name
        components.sort(key=lambda c: (-len(c), c[0]))

        component_count = len(components)
        is_decomposable = component_count >= 2 and len(unique_targets) >= 2

        # Modularity score: 0.0 if 1 component, approaching 1.0 as change is partitioned into even disconnected parts
        if component_count <= 1:
            modularity_score = 0.0
        else:
            max_size = max(len(c) for c in components)
            modularity_score = 1.0 - (max_size / len(unique_targets))

        # 3. Build ChangeClusters with ordering heuristics
        clusters: List[ChangeCluster] = []

        # Heuristic scoring for order: foundation files (models, core, schemas, migrations) should merge first
        def compute_cluster_order_weight(files: List[str]) -> int:
            weight = 50
            for f in files:
                f_lower = f.lower()
                if "model" in f_lower or "schema" in f_lower or "migration" in f_lower:
                    weight -= 20
                elif "core" in f_lower or "util" in f_lower or "contract" in f_lower:
                    weight -= 10
                elif "endpoint" in f_lower or "api" in f_lower or "service" in f_lower:
                    weight += 10
                elif "test" in f_lower or "frontend" in f_lower or "component" in f_lower:
                    weight += 20
            return weight

        # Sort clusters by foundational ordering weight
        weighted_components = [
            (compute_cluster_order_weight(comp_files), comp_files) for comp_files in components
        ]
        weighted_components.sort(key=lambda item: (item[0], -len(item[1]), item[1][0]))

        for idx, (_, comp_files) in enumerate(weighted_components, start=1):
            cluster_id = f"cluster-{idx}"

            # Dominant component
            component_counts: Dict[str, int] = defaultdict(int)
            for f in comp_files:
                component_counts[cls.get_component_name(f)] += 1
            dominant_component = max(component_counts.items(), key=lambda x: x[1])[0]

            # Internal edge count
            c_set = set(comp_files)
            edge_count = 0
            for src in comp_files:
                for tgt in directed_internal.get(src, set()):
                    if tgt in c_set:
                        edge_count += 1

            # External dependencies for this cluster
            c_ext_deps: Set[str] = set()
            for f in comp_files:
                c_ext_deps.update(external_deps_map.get(f, set()))
            ext_deps_sorted = sorted(list(c_ext_deps))[:5]

            # Suggested PR title & branch
            comp_slug = dominant_component.replace("/", "-").replace("\\", "-").strip("-")
            if not comp_slug or comp_slug == "root":
                comp_slug = Path(comp_files[0]).stem

            file_stems = [Path(f).stem for f in comp_files]
            if len(comp_files) == 1:
                name_str = f"{dominant_component} ({file_stems[0]})"
                pr_title = f"feat({comp_slug}): update {file_stems[0]}"
                branch_name = f"feat/{comp_slug}-{file_stems[0]}".lower()
            else:
                name_str = f"{dominant_component} ({len(comp_files)} files)"
                pr_title = f"feat({comp_slug}): modular update ({len(comp_files)} files)"
                branch_name = f"feat/{comp_slug}-subsystem".lower()

            rationale = (
                f"Cluster of {len(comp_files)} file(s) centered in '{dominant_component}' "
                f"with {edge_count} internal dependencies and zero direct coupling to sibling clusters."
            )

            clusters.append(
                ChangeCluster(
                    cluster_id=cluster_id,
                    name=name_str,
                    dominant_component=dominant_component,
                    files=comp_files,
                    internal_edge_count=edge_count,
                    external_dependencies=ext_deps_sorted,
                    suggested_pr_title=pr_title,
                    suggested_branch_name=branch_name,
                    rationale=rationale,
                    recommended_order=idx,
                )
            )

        if is_decomposable:
            summary = (
                f"Proposed change spans {len(unique_targets)} files across {component_count} independent, "
                f"weakly-connected subgraphs. Recommended to split into {component_count} decoupled PRs to minimize "
                f"blast radius and simplify code review (modularity score: {round(modularity_score, 2)})."
            )
        else:
            summary = (
                f"Proposed change of {len(unique_targets)} file(s) forms a single connected dependency component. "
                "Files are tightly coupled; splitting into separate PRs is not recommended."
            )

        return ChangeDecompositionReport(
            target_files=unique_targets,
            total_files=len(unique_targets),
            component_count=component_count,
            is_decomposable=is_decomposable,
            modularity_score=modularity_score,
            clusters=clusters,
            summary=summary,
        )
