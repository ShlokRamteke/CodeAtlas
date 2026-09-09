"""Guarding Test Reachability & Verification Gap Detection.

Analyzes test-to-target relationships, ranks test suites by their reach across
changed files, and detects verification gaps:
- Untested Changes: Modified files with no exercising tests.
- Stale Test Candidates: Covered files modified without their guarding tests being touched.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Mapping, Sequence, Set


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


def rank_tests_by_reach(
    test_to_covered_targets: Mapping[str, Set[str]],
    target_files: Set[str],
) -> list[ReachRankedTest]:
    """Order tests by how many changed files each test reaches/guards.

    Tests that reach more changed files are ranked at the top so engineers
    and agents execute the highest-impact tests first.
    """
    ranked: list[ReachRankedTest] = []

    for test_file, covered_targets in test_to_covered_targets.items():
        intersected = sorted(covered_targets.intersection(target_files))
        if intersected:
            ranked.append(
                ReachRankedTest(
                    test_file=test_file,
                    reached_target_count=len(intersected),
                    reached_targets=intersected,
                )
            )

    # Sort descending by reach count, then alphabetically by test path for determinism
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
    diff_files = files_in_diff or proposed_files
    untested: list[UntestedChangeWarning] = []
    stale_candidates: list[StaleTestCandidateWarning] = []

    for target in sorted(proposed_files):
        # Skip test files themselves from being evaluated as untested source files
        if "test" in target.lower() or "spec" in target.lower():
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
            # Code is covered by tests; check if any of the covering tests are included in the diff
            touched_tests = covering_tests.intersection(diff_files)
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
    untested, stale = detect_verification_gaps(proposed_files, file_to_covering_tests, files_in_diff)

    return GuardingTestReport(
        ranked_tests=ranked,
        untested_changes=untested,
        stale_test_candidates=stale,
        total_guarding_tests=len(ranked),
    )
