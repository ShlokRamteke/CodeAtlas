from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class ReachableNode:
    path: str
    depth: int
    direction: str  # "upstream" (caller/importer) or "downstream" (callee/dependency)
    via: Optional[str] = None
    component: str = ""


@dataclass
class BlastRadiusResult:
    target_files: List[str]
    upstream_callers: List[ReachableNode] = field(default_factory=list)
    downstream_dependencies: List[ReachableNode] = field(default_factory=list)
    transitive_files: List[str] = field(default_factory=list)
    affected_components: List[str] = field(default_factory=list)
    max_depth_reached: int = 0
    total_affected_count: int = 0


class BlastRadiusAnalyzer:
    """Computes static upstream and downstream reachability across dependency edges."""

    @staticmethod
    def get_component_name(path: str) -> str:
        """Extract logical component folder for a given file path."""
        parts = Path(path).parts
        if len(parts) > 1:
            return "/".join(parts[: min(2, len(parts) - 1)])
        return "root"

    @classmethod
    def compute_blast_radius(
        cls,
        target_files: List[str],
        dependency_edges: List[Tuple[str, str]],  # (source_path, target_path) where source imports target
        max_depth: int = 3,
    ) -> BlastRadiusResult:
        """Calculate transitive blast radius for given target files.

        Edges are directed: (source, target) means `source` depends on / imports `target`.
        - Upstream callers: files that import target (traverse in reverse: target -> source).
        - Downstream dependencies: files imported by target (traverse forward: target -> target).
        """
        forward_graph: Dict[str, Set[str]] = defaultdict(set)
        reverse_graph: Dict[str, Set[str]] = defaultdict(set)

        for src, tgt in dependency_edges:
            forward_graph[src].add(tgt)
            reverse_graph[tgt].add(src)

        targets_set = set(target_files)
        all_affected: Set[str] = set(target_files)

        # 1. Downstream traversal (what targets depend on)
        downstream_nodes: List[ReachableNode] = []
        downstream_visited: Set[str] = set(target_files)
        # queue: (current_node, current_depth, via_node)
        queue_down = deque([(t, 0, None) for t in target_files])

        max_depth_seen = 0

        while queue_down:
            curr, depth, via = queue_down.popleft()
            if depth > max_depth_seen:
                max_depth_seen = depth

            if depth > 0:
                downstream_nodes.append(
                    ReachableNode(
                        path=curr,
                        depth=depth,
                        direction="downstream",
                        via=via,
                        component=cls.get_component_name(curr),
                    )
                )
                all_affected.add(curr)

            if depth < max_depth:
                for nxt in sorted(forward_graph.get(curr, set())):
                    if nxt not in downstream_visited:
                        downstream_visited.add(nxt)
                        queue_down.append((nxt, depth + 1, curr))

        # 2. Upstream traversal (what depends on / calls targets)
        upstream_nodes: List[ReachableNode] = []
        upstream_visited: Set[str] = set(target_files)
        queue_up = deque([(t, 0, None) for t in target_files])

        while queue_up:
            curr, depth, via = queue_up.popleft()
            if depth > max_depth_seen:
                max_depth_seen = depth

            if depth > 0:
                upstream_nodes.append(
                    ReachableNode(
                        path=curr,
                        depth=depth,
                        direction="upstream",
                        via=via,
                        component=cls.get_component_name(curr),
                    )
                )
                all_affected.add(curr)

            if depth < max_depth:
                for nxt in sorted(reverse_graph.get(curr, set())):
                    if nxt not in upstream_visited:
                        upstream_visited.add(nxt)
                        queue_up.append((nxt, depth + 1, curr))

        # Determine affected components
        components: Set[str] = {cls.get_component_name(p) for p in all_affected}

        transitive_only = sorted(all_affected - targets_set)

        return BlastRadiusResult(
            target_files=list(target_files),
            upstream_callers=upstream_nodes,
            downstream_dependencies=downstream_nodes,
            transitive_files=transitive_only,
            affected_components=sorted(components),
            max_depth_reached=max_depth_seen,
            total_affected_count=len(all_affected),
        )
