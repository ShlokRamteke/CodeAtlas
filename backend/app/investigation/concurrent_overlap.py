from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.commit import Commit
from app.models.historical_link import CommitPullRequestLink
from app.models.pull_request import PullRequest, PullRequestState

logger = logging.getLogger(__name__)


def _normalize_path(path: str) -> str:
    """Normalize file path by removing leading slashes and dot prefixes."""
    p = path.strip()
    if p.startswith("./"):
        p = p[2:]
    return p.lstrip("/")


@dataclass
class ConcurrentPROverlap:
    """Represents concurrent overlap between proposed changes and an open pull request."""

    pr_number: int
    pr_title: str
    pr_author: str
    pr_html_url: Optional[str] = None
    head_branch: Optional[str] = None
    base_branch: Optional[str] = None
    overlap_type: str = "direct_target"  # "direct_target" | "blast_radius"
    direct_overlapping_files: List[str] = field(default_factory=list)
    blast_overlapping_files: List[str] = field(default_factory=list)
    overlapping_files: List[str] = field(default_factory=list)
    risk_level: str = "HIGH"  # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
    recommendation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pr_number": self.pr_number,
            "pr_title": self.pr_title,
            "pr_author": self.pr_author,
            "pr_html_url": self.pr_html_url,
            "head_branch": self.head_branch,
            "base_branch": self.base_branch,
            "overlap_type": self.overlap_type,
            "direct_overlapping_files": self.direct_overlapping_files,
            "blast_overlapping_files": self.blast_overlapping_files,
            "overlapping_files": self.overlapping_files,
            "risk_level": self.risk_level,
            "recommendation": self.recommendation,
        }


@dataclass
class ConcurrentOverlapReport:
    """Aggregate concurrent branch overlap and merge conflict detection report."""

    total_open_prs: int = 0
    overlapping_pr_count: int = 0
    has_direct_conflicts: bool = False
    has_blast_conflicts: bool = False
    highest_risk_level: str = "NONE"  # "NONE" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    overlapping_prs: List[ConcurrentPROverlap] = field(default_factory=list)
    target_files_analyzed: List[str] = field(default_factory=list)
    blast_radius_files_analyzed: List[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_open_prs": self.total_open_prs,
            "overlapping_pr_count": self.overlapping_pr_count,
            "has_direct_conflicts": self.has_direct_conflicts,
            "has_blast_conflicts": self.has_blast_conflicts,
            "highest_risk_level": self.highest_risk_level,
            "overlapping_prs": [p.to_dict() for p in self.overlapping_prs],
            "target_files_analyzed": self.target_files_analyzed,
            "blast_radius_files_analyzed": self.blast_radius_files_analyzed,
            "summary": self.summary,
        }


class ConcurrentOverlapDetector:
    """
    Detects concurrent branch overlap and pre-change merge conflict risks.
    Analyzes active, unmerged pull requests whose touched files intersect with
    proposed target files or their direct blast radius.
    """

    _RISK_PRIORITY = {
        "CRITICAL": 4,
        "HIGH": 3,
        "MEDIUM": 2,
        "LOW": 1,
        "NONE": 0,
    }

    async def detect_overlaps(
        self,
        db: AsyncSession,
        repository_id: uuid.UUID,
        target_files: List[str],
        blast_radius_files: Optional[List[str]] = None,
    ) -> ConcurrentOverlapReport:
        """
        Analyze all open PRs in repository against target files and blast radius files.
        """
        clean_targets: Set[str] = {_normalize_path(f) for f in target_files if f.strip()}
        clean_blast: Set[str] = {
            _normalize_path(f)
            for f in (blast_radius_files or [])
            if f.strip() and _normalize_path(f) not in clean_targets
        }

        # Query all open pull requests
        stmt = (
            select(PullRequest)
            .where(
                PullRequest.repository_id == repository_id,
                PullRequest.state == PullRequestState.OPEN,
            )
            .options(
                selectinload(PullRequest.commit_links)
                .selectinload(CommitPullRequestLink.commit)
                .selectinload(Commit.file_changes)
            )
            .order_by(PullRequest.number.desc())
        )
        result = await db.execute(stmt)
        open_prs = list(result.scalars().all())

        overlapping_prs: List[ConcurrentPROverlap] = []

        for pr in open_prs:
            pr_files: Set[str] = set()

            # 1. From explicitly recorded touched_files
            if pr.touched_files:
                for tf in pr.touched_files:
                    pr_files.add(_normalize_path(str(tf)))

            # 2. From linked commits and their file changes
            for cl in pr.commit_links:
                if cl.commit and cl.commit.file_changes:
                    for fc in cl.commit.file_changes:
                        file_p = getattr(fc, "file_path", None) or getattr(fc, "path", "")
                        if file_p:
                            pr_files.add(_normalize_path(file_p))

            if not pr_files:
                continue

            direct_matches = sorted(pr_files & clean_targets)
            blast_matches = sorted((pr_files & clean_blast) - set(direct_matches))

            if not direct_matches and not blast_matches:
                continue

            if direct_matches:
                overlap_type = "direct_target"
                risk_level = "CRITICAL" if len(direct_matches) > 1 else "HIGH"
                branch_info = f"branch '{pr.head_branch}'" if pr.head_branch else "an active branch"
                recommendation = (
                    f"Direct file conflict with PR #{pr.number} ('{pr.title}') by @{pr.author} "
                    f"on {branch_info}. Both changes touch: {', '.join(direct_matches)}. "
                    f"Coordinate with author or rebase after PR #{pr.number} merges."
                )
            else:
                overlap_type = "blast_radius"
                risk_level = "MEDIUM"
                branch_info = f"branch '{pr.head_branch}'" if pr.head_branch else "an active branch"
                recommendation = (
                    f"Architectural dependency overlap with PR #{pr.number} ('{pr.title}') by @{pr.author} "
                    f"on {branch_info}. Modifies {len(blast_matches)} blast-radius dependency file(s): "
                    f"{', '.join(blast_matches)}. Verify interface contracts remain compatible."
                )

            overlap_record = ConcurrentPROverlap(
                pr_number=pr.number,
                pr_title=pr.title,
                pr_author=pr.author,
                pr_html_url=pr.html_url,
                head_branch=pr.head_branch,
                base_branch=pr.base_branch,
                overlap_type=overlap_type,
                direct_overlapping_files=direct_matches,
                blast_overlapping_files=blast_matches,
                overlapping_files=sorted(set(direct_matches + blast_matches)),
                risk_level=risk_level,
                recommendation=recommendation,
            )
            overlapping_prs.append(overlap_record)

        # Sort by highest risk first, then by PR number descending
        overlapping_prs.sort(
            key=lambda o: (self._RISK_PRIORITY.get(o.risk_level, 0), o.pr_number),
            reverse=True,
        )

        has_direct = any(o.overlap_type == "direct_target" for o in overlapping_prs)
        has_blast = any(o.overlap_type == "blast_radius" for o in overlapping_prs)

        if any(o.risk_level == "CRITICAL" for o in overlapping_prs):
            highest_risk = "CRITICAL"
        elif any(o.risk_level == "HIGH" for o in overlapping_prs):
            highest_risk = "HIGH"
        elif any(o.risk_level == "MEDIUM" for o in overlapping_prs):
            highest_risk = "MEDIUM"
        elif any(o.risk_level == "LOW" for o in overlapping_prs):
            highest_risk = "LOW"
        else:
            highest_risk = "NONE"

        if has_direct:
            direct_count = sum(1 for o in overlapping_prs if o.overlap_type == "direct_target")
            summary = (
                f"DETECTED {direct_count} open PR(s) with direct target file collisions. "
                f"Highest risk: {highest_risk}. Immediate merge conflict risk if modified concurrently."
            )
        elif has_blast:
            summary = (
                f"DETECTED {len(overlapping_prs)} open PR(s) modifying blast-radius dependencies. "
                f"Highest risk: {highest_risk}. Semantic or interface drift possible."
            )
        else:
            summary = "No concurrent branch conflicts detected across open pull requests."

        return ConcurrentOverlapReport(
            total_open_prs=len(open_prs),
            overlapping_pr_count=len(overlapping_prs),
            has_direct_conflicts=has_direct,
            has_blast_conflicts=has_blast,
            highest_risk_level=highest_risk,
            overlapping_prs=overlapping_prs,
            target_files_analyzed=sorted(clean_targets),
            blast_radius_files_analyzed=sorted(clean_blast),
            summary=summary,
        )
