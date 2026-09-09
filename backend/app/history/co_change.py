"""Historical Co-Change Mining & Hidden Coupling Detection.

Mines Git commit diff histories to discover pairs of files that frequently
change together. Identifies hidden / unexplained coupling where files co-change
frequently despite having no static import or dependency edge.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence, Set


@dataclass(frozen=True)
class CoChangePartner:
    """Historical partner file that changes alongside a target file."""

    target_file: str
    partner_file: str
    co_change_count: int
    total_target_changes: int
    frequency: float  # co_change_count / total_target_changes


@dataclass(frozen=True)
class HiddenCouplingWarning:
    """Alert for a co-change partner omitted from a proposed change set."""

    target_file: str
    omitted_partner: str
    frequency: float
    co_change_count: int
    has_static_import: bool
    explanation: str


def mine_co_change_partners(
    commit_file_sets: Sequence[Set[str]],
    min_co_changes: int = 2,
    min_frequency: float = 0.5,
) -> dict[str, list[CoChangePartner]]:
    """Mine co-occurring file changes across commit diffs.

    Returns mapping of file_path -> list of co-change partners sorted by frequency.
    """
    file_change_counts: dict[str, int] = defaultdict(int)
    pair_counts: dict[tuple[str, str], int] = defaultdict(int)

    for file_set in commit_file_sets:
        files = sorted(file_set)
        for f in files:
            file_change_counts[f] += 1

        for i, fa in enumerate(files):
            for fb in files[i + 1 :]:
                pair_counts[(fa, fb)] += 1
                pair_counts[(fb, fa)] += 1

    partners: dict[str, list[CoChangePartner]] = defaultdict(list)

    for (fa, fb), co_count in pair_counts.items():
        if co_count < min_co_changes:
            continue
        total_a = file_change_counts[fa]
        if total_a <= 0:
            continue
        freq = round(co_count / total_a, 3)
        if freq >= min_frequency:
            partners[fa].append(
                CoChangePartner(
                    target_file=fa,
                    partner_file=fb,
                    co_change_count=co_count,
                    total_target_changes=total_a,
                    frequency=freq,
                )
            )

    # Sort each list by frequency descending
    for fa in partners:
        partners[fa].sort(key=lambda p: (-p.frequency, -p.co_change_count, p.partner_file))

    return dict(partners)


def detect_hidden_coupling(
    proposed_files: Set[str],
    co_change_matrix: dict[str, list[CoChangePartner]],
    known_static_edges: Set[tuple[str, str]],
) -> list[HiddenCouplingWarning]:
    """Detect omitted co-change partners and classify whether coupling is hidden.

    Args:
        proposed_files: Files proposed to be modified.
        co_change_matrix: Precomputed co-change partners.
        known_static_edges: Set of known static (source_file, target_file) import/call edges.

    Returns:
        List of warnings for omitted partner files, flagging unexplained coupling.
    """
    warnings: list[HiddenCouplingWarning] = []
    seen_omitted: set[tuple[str, str]] = set()

    for target in proposed_files:
        if target not in co_change_matrix:
            continue

        for partner in co_change_matrix[target]:
            omitted = partner.partner_file
            # If partner is already in the proposed change set, no omission warning
            if omitted in proposed_files:
                continue

            pair_key = (target, omitted)
            if pair_key in seen_omitted:
                continue
            seen_omitted.add(pair_key)

            # Check if there is a static relationship between target and omitted
            has_static = (target, omitted) in known_static_edges or (
                omitted,
                target,
            ) in known_static_edges

            pct = int(partner.frequency * 100)
            if not has_static:
                explanation = (
                    f"Hidden Coupling: '{omitted}' co-changes with '{target}' in {pct}% "
                    f"of history ({partner.co_change_count}/{partner.total_target_changes} commits), "
                    f"yet no static import edge connects them. Verify if '{omitted}' should be included."
                )
            else:
                explanation = (
                    f"Coupled Partner: '{omitted}' frequently co-changes with '{target}' ({pct}% of commits) "
                    f"and is connected by static import, but was omitted from the proposed change set."
                )

            warnings.append(
                HiddenCouplingWarning(
                    target_file=target,
                    omitted_partner=omitted,
                    frequency=partner.frequency,
                    co_change_count=partner.co_change_count,
                    has_static_import=has_static,
                    explanation=explanation,
                )
            )

    warnings.sort(key=lambda w: (-w.frequency, -w.co_change_count))
    return warnings
