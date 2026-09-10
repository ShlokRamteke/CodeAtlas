"""Historical Co-Change Mining & Hidden Coupling Detection.

Mines Git commit diff histories to discover pairs of files that frequently
change together. Identifies hidden / unexplained coupling where files co-change
frequently despite having no static import or dependency edge.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence, Set, Tuple


@dataclass(frozen=True)
class CoChangePartner:
    """Historical partner file that changes alongside a target file."""

    target_file: str
    partner_file: str
    co_change_count: int
    total_target_changes: int
    frequency: float  # co_change_count / total_target_changes
    decayed_weight: float = 0.0


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
    commit_file_sets: Sequence[Set[str] | Tuple[Set[str], datetime]],
    min_co_changes: int = 2,
    min_frequency: float = 0.5,
    half_life_days: float = 180.0,
    reference_time: datetime | None = None,
) -> dict[str, list[CoChangePartner]]:
    """Mine co-occurring file changes across commit diffs.

    Supports optional commit timestamps for exponential recency decay (half_life_days = 180.0).
    Formula: weight = 2^(-age_in_days / half_life_days).

    Returns mapping of file_path -> list of co-change partners sorted by frequency / weight.
    """
    file_change_counts: dict[str, int] = defaultdict(int)
    file_change_weights: dict[str, float] = defaultdict(float)
    pair_counts: dict[tuple[str, str], int] = defaultdict(int)
    pair_weights: dict[tuple[str, str], float] = defaultdict(float)

    ref_time = reference_time or datetime.now(timezone.utc)
    if ref_time.tzinfo is None:
        ref_time = ref_time.replace(tzinfo=timezone.utc)

    for item in commit_file_sets:
        if isinstance(item, tuple) and len(item) == 2 and isinstance(item[1], datetime):
            file_set, c_time = item
            if c_time.tzinfo is None:
                c_time = c_time.replace(tzinfo=timezone.utc)
            age_days = max(0.0, (ref_time - c_time).total_seconds() / 86400.0)
            weight = math.pow(2.0, -age_days / half_life_days)
        else:
            file_set = item  # type: ignore[assignment]
            weight = 1.0

        files = sorted(file_set)
        for f in files:
            file_change_counts[f] += 1
            file_change_weights[f] += weight

        for i, fa in enumerate(files):
            for fb in files[i + 1 :]:
                pair_counts[(fa, fb)] += 1
                pair_counts[(fb, fa)] += 1
                pair_weights[(fa, fb)] += weight
                pair_weights[(fb, fa)] += weight

    partners: dict[str, list[CoChangePartner]] = defaultdict(list)

    for (fa, fb), co_count in pair_counts.items():
        if co_count < min_co_changes:
            continue
        total_a = file_change_counts[fa]
        if total_a <= 0:
            continue

        freq = round(co_count / total_a, 3)
        decayed_w = round(pair_weights[(fa, fb)], 3)

        if freq >= min_frequency:
            partners[fa].append(
                CoChangePartner(
                    target_file=fa,
                    partner_file=fb,
                    co_change_count=co_count,
                    total_target_changes=total_a,
                    frequency=freq,
                    decayed_weight=decayed_w,
                )
            )

    # Sort each list by frequency descending, then decayed_weight descending
    for fa in partners:
        partners[fa].sort(
            key=lambda p: (-p.frequency, -p.decayed_weight, -p.co_change_count, p.partner_file)
        )

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
