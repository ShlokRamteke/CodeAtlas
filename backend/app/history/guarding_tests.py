from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Set


@dataclass(frozen=True)
class ReachRankedTest:
    """Test suite ranked by the number of changed target files it guards."""

    test_file: str
    reached_target_count: int
    reached_targets: list[str]


@dataclass(frozen=True)
class UntestedChangeWarning:
    """Warning for a modified file that has zero guarding test coverage."""

    target_file: str
    explanation: str


@dataclass(frozen=True)
class StaleTestCandidateWarning:
    """Warning for code changed while covering tests were not touched in the PR."""

    target_file: str
    guarding_tests: list[str]
    explanation: str


@dataclass(frozen=True)
class GuardingTestReport:
    """Consolidated test reachability and verification gap report."""

    ranked_tests: list[ReachRankedTest]
    untested_changes: list[UntestedChangeWarning]
    stale_test_candidates: list[StaleTestCandidateWarning]
    total_guarding_tests: int

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary for signals and API serialization."""
        return {
            "ranked_tests": [
                {
                    "test_file": t.test_file,
                    "reached_target_count": t.reached_target_count,
                    "reached_targets": t.reached_targets,
                }
                for t in self.ranked_tests
            ],
            "untested_changes": [
                {
                    "target_file": w.target_file,
                    "explanation": w.explanation,
                }
                for w in self.untested_changes
            ],
            "stale_test_candidates": [
                {
                    "target_file": w.target_file,
                    "guarding_tests": w.guarding_tests,
                    "explanation": w.explanation,
                }
                for w in self.stale_test_candidates
            ],
            "total_guarding_tests": self.total_guarding_tests,
            "has_coverage_gaps": len(self.untested_changes) > 0 or len(self.stale_test_candidates) > 0,
            "untested_files": [w.target_file for w in self.untested_changes],
        }


def is_test_file(path: str) -> bool:
    """Determine if a file path is a test or spec file."""
    p = path.lower()
    return (
        ".test." in p
        or ".spec." in p
        or "/tests/" in p
        or "/__tests__/" in p
        or p.startswith("tests/")
        or p.startswith("test_")
        or "/test_" in p
        or p.endswith("_test.py")
        or p.endswith("_test.go")
        or p.endswith(".test.ts")
        or p.endswith(".test.js")
        or p.endswith(".spec.ts")
        or p.endswith(".spec.js")
    )


def match_test_by_naming(test_path: str, target_path: str) -> bool:
    """Check if test_path corresponds to target_path by naming conventions."""
    if not is_test_file(test_path):
        return False

    test_stem = Path(test_path).stem.lower()
    target_stem = Path(target_path).stem.lower()

    # Clean test stem
    cleaned = test_stem
    for suffix in [".test", ".spec", "_test"]:
        cleaned = cleaned.replace(suffix, "")
    if cleaned.startswith("test_"):
        cleaned = cleaned[5:]

    return cleaned == target_stem and bool(cleaned)


def build_test_coverage_mapping(
    target_files: Set[str],
    dependency_edges: Iterable[tuple[str, str]] | None = None,
    all_files: Iterable[str] | None = None,
    max_depth: int = 2,
) -> dict[str, set[str]]:
    """Build a mapping of target source files to covering test files.

    Traces:
    1. Static dependency edges where test file imports or calls target file.
    2. Transitive dependencies up to max_depth (e.g. test -> helper -> target).
    3. Naming convention heuristics (e.g. test_checkout.py matches checkout.py).
    """
    clean_targets = {f.lstrip("/"): f for f in target_files}
    file_to_tests: dict[str, set[str]] = {f: set() for f in target_files}

    edges = list(dependency_edges or [])
    reverse_graph: dict[str, set[str]] = defaultdict(set)

    for src, dst in edges:
        clean_src = src.lstrip("/")
        clean_dst = dst.lstrip("/")
        reverse_graph[clean_dst].add(clean_src)

    all_file_list = [f.lstrip("/") for f in (all_files or [])]
    discovered_tests: set[str] = {src for src, _ in edges if is_test_file(src)}
    discovered_tests.update(f for f in all_file_list if is_test_file(f))

    for raw_target in target_files:
        clean_t = raw_target.lstrip("/")
        # 1. Reverse graph search from target file
        visited = set()
        queue = [(clean_t, 0)]
        while queue:
            curr, depth = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)

            if depth > 0 and is_test_file(curr):
                file_to_tests[raw_target].add(curr)

            if depth < max_depth:
                for parent in reverse_graph.get(curr, set()):
                    if parent not in visited:
                        queue.append((parent, depth + 1))

        # 2. Naming convention heuristics
        for t_file in discovered_tests:
            if match_test_by_naming(t_file, clean_t):
                file_to_tests[raw_target].add(t_file)

    return file_to_tests


def rank_tests_by_reach(
    test_to_covered_targets: Mapping[str, Set[str]],
    target_files: Set[str],
) -> list[ReachRankedTest]:
    """Order tests by how many changed files each test reaches/guards.

    Tests that reach more changed files are ranked at the top so engineers
    and agents execute the highest-impact tests first.
    """
    ranked: list[ReachRankedTest] = []
    clean_target_map = {t.lstrip("/"): t for t in target_files}

    for test_file, covered_targets in test_to_covered_targets.items():
        intersected: set[str] = set()
        for c in covered_targets:
            clean_c = c.lstrip("/")
            if c in target_files:
                intersected.add(c)
            elif clean_c in clean_target_map:
                intersected.add(clean_target_map[clean_c])

        if intersected:
            sorted_targets = sorted(intersected)
            ranked.append(
                ReachRankedTest(
                    test_file=test_file,
                    reached_target_count=len(sorted_targets),
                    reached_targets=sorted_targets,
                )
            )

    ranked.sort(key=lambda t: (-t.reached_target_count, t.test_file))
    return ranked


def detect_verification_gaps(
    proposed_files: Set[str],
    file_to_covering_tests: Mapping[str, Set[str]],
    files_in_diff: Set[str] | None = None,
) -> tuple[list[UntestedChangeWarning], list[StaleTestCandidateWarning]]:
    """Detect untested changes and stale test candidates.

    Args:
        proposed_files: Files modified in the proposed change.
        file_to_covering_tests: Mapping of source file -> test files covering it.
        files_in_diff: Entire set of files in proposed diff (including test files).
    """
    diff_files = {f.lstrip("/") for f in (files_in_diff or proposed_files)}
    untested: list[UntestedChangeWarning] = []
    stale_candidates: list[StaleTestCandidateWarning] = []

    for target in sorted(proposed_files):
        # Skip test files themselves from being evaluated as untested source files
        if is_test_file(target):
            continue

        covering_tests = file_to_covering_tests.get(target, set())

        if not covering_tests:
            untested.append(
                UntestedChangeWarning(
                    target_file=target,
                    explanation=f"Untested Change: '{target}' has no known guarding tests in the repository.",
                )
            )
        else:
            clean_covering = {t.lstrip("/") for t in covering_tests}
            touched_tests = clean_covering.intersection(diff_files)
            if not touched_tests:
                guarding_list = sorted(covering_tests)
                stale_candidates.append(
                    StaleTestCandidateWarning(
                        target_file=target,
                        guarding_tests=guarding_list,
                        explanation=(
                            f"Stale Test Candidate: '{target}' changed, but none of its {len(guarding_list)} "
                            f"guarding test files ({', '.join(guarding_list[:3])}) were updated in the proposed change."
                        ),
                    )
                )

    return untested, stale_candidates


def analyze_guarding_tests(
    proposed_files: Set[str],
    file_to_covering_tests: Mapping[str, Set[str]],
    files_in_diff: Set[str] | None = None,
) -> GuardingTestReport:
    """Analyze reach-ranked test execution priority and verification gaps."""
    # Build inverse mapping: test_file -> covered target files
    test_to_targets: dict[str, set[str]] = {}
    for src, tests in file_to_covering_tests.items():
        for t in tests:
            test_to_targets.setdefault(t, set()).add(src)

    ranked = rank_tests_by_reach(test_to_targets, proposed_files)
    untested, stale = detect_verification_gaps(
        proposed_files, file_to_covering_tests, files_in_diff
    )

    return GuardingTestReport(
        ranked_tests=ranked,
        untested_changes=untested,
        stale_test_candidates=stale,
        total_guarding_tests=len(ranked),
    )

