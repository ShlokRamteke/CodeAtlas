"""Quantitative Change Risk Analysis & Defect Pressure Scoring.

Implements empirical software engineering defect prediction models:
- Kamei et al. (IEEE TSE 2013): "A Large-Scale Empirical Study of Just-in-Time Quality Assurance"
- Shannon churn entropy for change dispersion
- Recency-decayed historical defect pressure
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Sequence


@dataclass(frozen=True)
class FileChangeStat:
    """Individual file change churn statistics."""

    path: str
    lines_added: int
    lines_deleted: int

    @property
    def total_churn(self) -> int:
        return self.lines_added + self.lines_deleted


@dataclass(frozen=True)
class KameiMetrics:
    """Kamei empirical change metrics for a proposed change."""

    lines_added: int
    lines_deleted: int
    files_touched: int
    distinct_directories: int
    distinct_subsystems: int
    shannon_entropy: float


@dataclass(frozen=True)
class HistoricalCommitInfo:
    """Historical commit summary used for defect pressure computation."""

    hash: str
    message: str
    timestamp: datetime
    touched_files: tuple[str, ...]
    is_fix: bool = False


@dataclass(frozen=True)
class ChangeRiskReport:
    """Consolidated quantitative change risk assessment."""

    risk_score: float  # 0.0 (safest) to 1.0 (highest risk)
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    kamei_metrics: KameiMetrics
    defect_pressure: float
    explanatory_factors: list[str]


def compute_shannon_entropy(per_file_churns: Sequence[int]) -> float:
    """Calculate Shannon entropy of the per-file churn distribution.

    Normalized to quantify whether change is concentrated in one file (H ~ 0)
    or scattered widely across many files (H > 2.0).
    """
    total = sum(per_file_churns)
    if total <= 0 or len(per_file_churns) <= 1:
        return 0.0

    entropy = 0.0
    for churn in per_file_churns:
        if churn > 0:
            p = churn / total
            entropy -= p * math.log2(p)
    return round(entropy, 4)


def compute_kamei_metrics(changes: Sequence[FileChangeStat]) -> KameiMetrics:
    """Compute Kamei empirical metrics over a collection of file change stats."""
    if not changes:
        return KameiMetrics(
            lines_added=0,
            lines_deleted=0,
            files_touched=0,
            distinct_directories=0,
            distinct_subsystems=0,
            shannon_entropy=0.0,
        )

    lines_added = sum(c.lines_added for c in changes)
    lines_deleted = sum(c.lines_deleted for c in changes)
    files_touched = len(changes)

    directories: set[str] = set()
    subsystems: set[str] = set()
    churns: list[int] = []

    for c in changes:
        churns.append(c.total_churn)
        parts = PurePosixPath(c.path).parts
        if len(parts) > 1:
            directories.add(str(PurePosixPath(*parts[:-1])))
            subsystems.add(parts[0])
        else:
            directories.add(".")
            subsystems.add(".")

    entropy = compute_shannon_entropy(churns)

    return KameiMetrics(
        lines_added=lines_added,
        lines_deleted=lines_deleted,
        files_touched=files_touched,
        distinct_directories=len(directories),
        distinct_subsystems=len(subsystems),
        shannon_entropy=entropy,
    )


def is_fix_commit(message: str) -> bool:
    """Deterministic check if commit message represents a defect or bug fix."""
    msg = message.lower()
    keywords = (
        "fix:",
        "fix(",
        "fixes",
        "fixed",
        "bug:",
        "bugfix",
        "hotfix",
        "patch",
        "resolves",
        "resolved",
        "close #",
        "closes #",
        "revert",
    )
    return any(kw in msg for kw in keywords)


def compute_defect_pressure(
    commits: Sequence[HistoricalCommitInfo],
    target_files: set[str],
    reference_time: datetime | None = None,
    half_life_days: float = 365.0,
) -> float:
    """Calculate historical bug-fix pressure discounted by exponential recency decay.

    Formula: sum( 2^(-age_in_days / half_life) ) for each fix commit touching target files.
    """
    if not commits or not target_files:
        return 0.0

    ref_time = reference_time or datetime.now(timezone.utc)
    if ref_time.tzinfo is None:
        ref_time = ref_time.replace(tzinfo=timezone.utc)

    pressure = 0.0

    for commit in commits:
        # Check if commit is a bug-fix and touches at least one target file
        is_fix = commit.is_fix or is_fix_commit(commit.message)
        if not is_fix:
            continue

        if not any(f in target_files for f in commit.touched_files):
            continue

        c_time = commit.timestamp
        if c_time.tzinfo is None:
            c_time = c_time.replace(tzinfo=timezone.utc)

        age_days = max(0.0, (ref_time - c_time).total_seconds() / 86400.0)
        weight = math.pow(2.0, -age_days / half_life_days)
        pressure += weight

    return round(pressure, 3)


def assess_change_risk(
    changes: Sequence[FileChangeStat],
    commits: Sequence[HistoricalCommitInfo] = (),
    reference_time: datetime | None = None,
) -> ChangeRiskReport:
    """Produce a consolidated change risk assessment combining Kamei churn and defect pressure."""
    kamei = compute_kamei_metrics(changes)
    target_files = {c.path for c in changes}
    pressure = compute_defect_pressure(commits, target_files, reference_time=reference_time)

    factors: list[str] = []
    score = 0.0

    # 1. Churn scale
    total_lines = kamei.lines_added + kamei.lines_deleted
    if total_lines > 500:
        score += 0.25
        factors.append(f"Large code churn ({total_lines} lines modified)")
    elif total_lines > 150:
        score += 0.15
        factors.append(f"Moderate code churn ({total_lines} lines modified)")
    else:
        score += 0.05

    # 2. Diffusion across subsystems & directories
    if kamei.distinct_subsystems >= 3:
        score += 0.25
        factors.append(f"High diffusion across {kamei.distinct_subsystems} distinct subsystems")
    elif kamei.distinct_directories >= 3:
        score += 0.15
        factors.append(f"Diffused across {kamei.distinct_directories} distinct directories")

    # 3. Shannon churn entropy
    if kamei.shannon_entropy > 2.0:
        score += 0.20
        factors.append(f"High churn entropy ({kamei.shannon_entropy}): change is scattered across unrelated files")
    elif kamei.shannon_entropy > 1.0:
        score += 0.10

    # 4. Historical defect pressure
    if pressure >= 3.0:
        score += 0.30
        factors.append(f"Severe historical defect pressure ({pressure:.1f}): target files have frequent prior regressions")
    elif pressure >= 1.0:
        score += 0.15
        factors.append(f"Moderate historical defect pressure ({pressure:.1f}) on modified files")

    final_score = min(1.0, round(score, 2))

    if final_score >= 0.75:
        level = "CRITICAL"
    elif final_score >= 0.50:
        level = "HIGH"
    elif final_score >= 0.25:
        level = "MEDIUM"
    else:
        level = "LOW"

    return ChangeRiskReport(
        risk_score=final_score,
        risk_level=level,
        kamei_metrics=kamei,
        defect_pressure=pressure,
        explanatory_factors=factors,
    )
