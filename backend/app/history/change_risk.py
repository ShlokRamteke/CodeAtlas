"""Quantitative Change Risk Analysis & Defect Pressure Scoring.

Implements empirical software engineering defect prediction models:
- Kamei et al. (IEEE TSE 2013): "A Large-Scale Empirical Study of Just-in-Time Quality Assurance"
- Shannon churn entropy for change dispersion
- Recency-decayed historical defect pressure
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


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
    fix_commit_count: int = 0


def parse_unified_diff(diff_str: str) -> list[FileChangeStat]:
    """Parse unified git diff format and extract churn stats per file."""
    if not diff_str or not diff_str.strip():
        return []

    file_stats: dict[str, dict[str, int]] = {}
    current_file: str | None = None

    for line in diff_str.splitlines():
        if line.startswith("diff --git "):
            parts = line.strip().split()
            if len(parts) >= 4:
                target = parts[3]
                current_file = target[2:] if target.startswith("b/") else target
                if current_file not in file_stats:
                    file_stats[current_file] = {"added": 0, "deleted": 0}
            continue

        if line.startswith("+++ "):
            target = line[4:].strip()
            if target != "/dev/null":
                current_file = target[2:] if target.startswith("b/") else target
                if current_file not in file_stats:
                    file_stats[current_file] = {"added": 0, "deleted": 0}
            continue

        if line.startswith("--- "):
            target = line[4:].strip()
            if target != "/dev/null" and current_file is None:
                current_file = target[2:] if target.startswith("a/") else target
                if current_file not in file_stats:
                    file_stats[current_file] = {"added": 0, "deleted": 0}
            continue

        if current_file:
            if line.startswith("+") and not line.startswith("+++"):
                file_stats[current_file]["added"] += 1
            elif line.startswith("-") and not line.startswith("---"):
                file_stats[current_file]["deleted"] += 1

    return [
        FileChangeStat(
            path=path,
            lines_added=counts["added"],
            lines_deleted=counts["deleted"],
        )
        for path, counts in file_stats.items()
    ]


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
    fix_commits = [
        c
        for c in commits
        if (c.is_fix or is_fix_commit(c.message))
        and any(f in target_files for f in c.touched_files)
    ]

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
        factors.append(
            f"High churn entropy ({kamei.shannon_entropy}): change is scattered across unrelated files"
        )
    elif kamei.shannon_entropy > 1.0:
        score += 0.10

    # 4. Historical defect pressure
    if pressure >= 3.0:
        score += 0.30
        factors.append(
            f"Severe historical defect pressure ({pressure:.1f}): target files have frequent prior regressions"
        )
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
        fix_commit_count=len(fix_commits),
    )


async def mine_defect_pressure_from_db(
    db: AsyncSession,
    repository_id: uuid.UUID,
    target_files: set[str],
    limit: int = 20000,
    half_life_days: float = 365.0,
    reference_time: datetime | None = None,
) -> tuple[float, list[HistoricalCommitInfo]]:
    """Deep walk of up to 20,000 commits from database, mining defect pressure for target files.

    Returns (defect_pressure_score, list_of_matching_fix_commits).
    """
    if not target_files:
        return 0.0, []

    from sqlalchemy import select

    from app.models.commit import Commit
    from app.models.commit_file_change import CommitFileChange

    clean_targets = {f.lstrip("/") for f in target_files}

    query = (
        select(
            Commit.commit_hash,
            Commit.message,
            Commit.committed_at,
            CommitFileChange.file_path,
        )
        .join(CommitFileChange, Commit.id == CommitFileChange.commit_id)
        .where(
            Commit.repository_id == repository_id,
            CommitFileChange.file_path.in_(clean_targets),
        )
        .order_by(Commit.committed_at.desc())
        .limit(limit)
    )
    res = await db.execute(query)
    rows = res.all()

    commit_dict: dict[str, dict] = {}
    for c_hash, message, committed_at, file_path in rows:
        if c_hash not in commit_dict:
            commit_dict[c_hash] = {
                "hash": c_hash,
                "message": message,
                "timestamp": committed_at,
                "touched_files": set(),
                "is_fix": is_fix_commit(message),
            }
        if file_path:
            commit_dict[c_hash]["touched_files"].add(file_path)

    commit_infos = [
        HistoricalCommitInfo(
            hash=info["hash"],
            message=info["message"],
            timestamp=info["timestamp"],
            touched_files=tuple(info["touched_files"]),
            is_fix=info["is_fix"],
        )
        for info in commit_dict.values()
    ]

    pressure = compute_defect_pressure(
        commits=commit_infos,
        target_files=clean_targets,
        reference_time=reference_time,
        half_life_days=half_life_days,
    )

    fix_commits = [
        c for c in commit_infos if c.is_fix and any(f in clean_targets for f in c.touched_files)
    ]
    return pressure, fix_commits
