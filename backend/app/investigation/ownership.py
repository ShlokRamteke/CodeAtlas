from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _normalize_path(path: str) -> str:
    """Normalize file path by removing leading slashes and dot prefixes."""
    p = path.strip()
    if p.startswith("./"):
        p = p[2:]
    return p.lstrip("/")


def _ensure_utc(dt: Optional[datetime]) -> datetime:
    """Ensure datetime is offset-aware in UTC."""
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass
class AuthorCommitStat:
    """Statistics for an individual author on a specific file or scope."""

    author_name: str
    author_email: str
    commit_count: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    raw_churn: int = 0
    decayed_churn: float = 0.0
    ownership_percentage: float = 0.0
    last_committed_at: Optional[str] = None
    days_since_last_commit: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "author_name": self.author_name,
            "author_email": self.author_email,
            "commit_count": self.commit_count,
            "lines_added": self.lines_added,
            "lines_deleted": self.lines_deleted,
            "raw_churn": self.raw_churn,
            "decayed_churn": round(self.decayed_churn, 2),
            "ownership_percentage": round(self.ownership_percentage, 1),
            "last_committed_at": self.last_committed_at,
            "days_since_last_commit": self.days_since_last_commit,
        }


@dataclass
class FileOwnership:
    """Authorship concentration breakdown for a specific file."""

    file_path: str
    total_commits: int = 0
    primary_owner: Optional[AuthorCommitStat] = None
    co_owners: List[AuthorCommitStat] = field(default_factory=list)
    all_contributors: List[AuthorCommitStat] = field(default_factory=list)
    ownership_level: str = "DIFFUSED"  # "HIGH" (>=70%), "MEDIUM" (40-70%), "DIFFUSED" (<40%)
    bus_factor: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "total_commits": self.total_commits,
            "primary_owner": self.primary_owner.to_dict() if self.primary_owner else None,
            "co_owners": [c.to_dict() for c in self.co_owners],
            "all_contributors": [c.to_dict() for c in self.all_contributors],
            "ownership_level": self.ownership_level,
            "bus_factor": self.bus_factor,
        }


@dataclass
class ReviewerRecommendation:
    """Recommended code reviewer with domain qualification rationale."""

    author_name: str
    author_email: str
    score: float = 0.0  # 0.0 to 1.0 normalized recommendation score
    role: str = "COMPONENT_EXPERT"  # "PRIMARY_OWNER", "COMPONENT_EXPERT", "BLAST_RADIUS_GUARDIAN"
    rationale: str = ""
    target_files_owned: List[str] = field(default_factory=list)
    blast_radius_files_owned: List[str] = field(default_factory=list)
    commits_count: int = 0
    days_since_last_commit: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "author_name": self.author_name,
            "author_email": self.author_email,
            "score": round(self.score, 3),
            "role": self.role,
            "rationale": self.rationale,
            "target_files_owned": self.target_files_owned,
            "blast_radius_files_owned": self.blast_radius_files_owned,
            "commits_count": self.commits_count,
            "days_since_last_commit": self.days_since_last_commit,
        }


@dataclass
class CodeOwnershipReport:
    """Comprehensive code ownership and reviewer recommendation report."""

    target_files: List[str] = field(default_factory=list)
    blast_radius_files: List[str] = field(default_factory=list)
    file_ownerships: List[FileOwnership] = field(default_factory=list)
    recommended_reviewers: List[ReviewerRecommendation] = field(default_factory=list)
    overall_bus_factor: int = 1
    knowledge_loss_warnings: List[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_files": self.target_files,
            "blast_radius_files": self.blast_radius_files,
            "file_ownerships": [f.to_dict() for f in self.file_ownerships],
            "recommended_reviewers": [r.to_dict() for r in self.recommended_reviewers],
            "overall_bus_factor": self.overall_bus_factor,
            "knowledge_loss_warnings": self.knowledge_loss_warnings,
            "summary": self.summary,
        }


@dataclass
class CommitChangeItem:
    """Normalized commit file change for analysis."""

    commit_hash: str
    author_name: str
    author_email: str
    committed_at: datetime
    file_path: str
    insertions: int = 0
    deletions: int = 0


class CodeOwnershipAnalyzer:
    """
    Computes authorship concentration and recommends qualified reviewers
    using Git commit file change history with exponential recency decay.
    """

    DEFAULT_HALF_LIFE_DAYS = 180.0

    @classmethod
    def analyze_ownership(
        cls,
        target_files: List[str],
        blast_radius_files: Optional[List[str]] = None,
        commit_records: Optional[List[CommitChangeItem | Dict[str, Any]]] = None,
        current_author: Optional[str] = None,
        half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
        reference_time: Optional[datetime] = None,
    ) -> CodeOwnershipReport:
        """
        Pure deterministic analysis of code ownership and reviewer recommendations.
        """
        clean_targets = [_normalize_path(f) for f in target_files if f and f.strip()]
        unique_targets = sorted(list(dict.fromkeys(clean_targets)))

        clean_blast = [
            _normalize_path(f)
            for f in (blast_radius_files or [])
            if f and f.strip() and _normalize_path(f) not in unique_targets
        ]
        unique_blast = sorted(list(dict.fromkeys(clean_blast)))

        records: List[CommitChangeItem] = []
        for r in commit_records or []:
            if isinstance(r, CommitChangeItem):
                r.committed_at = _ensure_utc(r.committed_at)
                records.append(r)
            elif isinstance(r, dict):
                dt = r.get("committed_at") or r.get("timestamp")
                if isinstance(dt, str):
                    try:
                        dt = datetime.fromisoformat(dt)
                    except ValueError:
                        dt = datetime.now(timezone.utc)
                elif not isinstance(dt, datetime):
                    dt = datetime.now(timezone.utc)
                dt = _ensure_utc(dt)

                records.append(
                    CommitChangeItem(
                        commit_hash=str(r.get("commit_hash", "")),
                        author_name=str(r.get("author_name", "Unknown")),
                        author_email=str(r.get("author_email", "")),
                        committed_at=dt,
                        file_path=_normalize_path(str(r.get("file_path", ""))),
                        insertions=int(r.get("insertions", 0)),
                        deletions=int(r.get("deletions", 0)),
                    )
                )

        if not unique_targets and not records:
            return CodeOwnershipReport(
                target_files=[],
                blast_radius_files=[],
                summary="No files provided for ownership analysis.",
            )

        # Establish reference timestamp for recency decay
        if reference_time is None:
            if records:
                reference_time = max(r.committed_at for r in records)
            else:
                reference_time = datetime.now(timezone.utc)
        reference_time = _ensure_utc(reference_time)

        # Group commit records by file
        file_to_records: Dict[str, List[CommitChangeItem]] = defaultdict(list)
        all_relevant_files = set(unique_targets) | set(unique_blast)
        for rec in records:
            if rec.file_path in all_relevant_files:
                file_to_records[rec.file_path].append(rec)

        # 1. Analyze per-file ownership
        file_ownerships: List[FileOwnership] = []
        target_author_decayed: Dict[Tuple[str, str], float] = defaultdict(float)
        blast_author_decayed: Dict[Tuple[str, str], float] = defaultdict(float)
        author_last_active: Dict[Tuple[str, str], datetime] = {}
        author_commit_counts: Dict[Tuple[str, str], int] = defaultdict(int)

        warnings: List[str] = []

        for fpath in unique_targets + unique_blast:
            f_recs = file_to_records.get(fpath, [])
            f_ownership = cls._analyze_file_ownership(
                file_path=fpath,
                records=f_recs,
                ref_time=reference_time,
                half_life_days=half_life_days,
            )
            if fpath in unique_targets:
                file_ownerships.append(f_ownership)

            is_target = fpath in unique_targets
            for contrib in f_ownership.all_contributors:
                auth_key = (contrib.author_name, contrib.author_email)
                author_commit_counts[auth_key] += contrib.commit_count

                if contrib.last_committed_at:
                    try:
                        c_dt = _ensure_utc(datetime.fromisoformat(contrib.last_committed_at))
                        if (
                            auth_key not in author_last_active
                            or c_dt > author_last_active[auth_key]
                        ):
                            author_last_active[auth_key] = c_dt
                    except ValueError:
                        pass

                if is_target:
                    target_author_decayed[auth_key] += contrib.decayed_churn
                else:
                    blast_author_decayed[auth_key] += contrib.decayed_churn

            # Knowledge loss check for target files
            if is_target and f_ownership.primary_owner:
                po = f_ownership.primary_owner
                days = po.days_since_last_commit
                if days is not None and days > 180:
                    warnings.append(
                        f"Knowledge loss risk: Primary author '{po.author_name}' of '{fpath}' has been inactive for {days} days."
                    )
                if f_ownership.ownership_level == "DIFFUSED" and len(f_recs) >= 3:
                    warnings.append(
                        f"Diffused ownership: '{fpath}' lacks a clear owner (top author holds <40% share). Team review recommended."
                    )

        # 2. Overall bus factor across target files
        overall_bus_factor = cls._calculate_bus_factor(target_author_decayed)

        if overall_bus_factor == 1 and target_author_decayed:
            sorted_target_authors = sorted(
                target_author_decayed.items(), key=lambda x: x[1], reverse=True
            )
            top_name, _ = sorted_target_authors[0]
            total_target_decayed = sum(target_author_decayed.values())
            top_share = (
                (sorted_target_authors[0][1] / total_target_decayed * 100.0)
                if total_target_decayed > 0
                else 0.0
            )
            if top_share >= 75.0:
                warnings.append(
                    f"Bus Factor = 1: Developer '{top_name[0]}' holds {top_share:.0f}% of changes across target files. Single point of failure."
                )

        # 3. Reviewer recommendation engine
        recommended_reviewers = cls._recommend_reviewers(
            target_files=unique_targets,
            blast_radius_files=unique_blast,
            file_ownerships=file_ownerships,
            file_to_records=file_to_records,
            target_author_decayed=target_author_decayed,
            blast_author_decayed=blast_author_decayed,
            author_last_active=author_last_active,
            author_commit_counts=author_commit_counts,
            current_author=current_author,
            ref_time=reference_time,
        )

        # 4. Summary string
        summary = cls._generate_summary(
            target_files=unique_targets,
            blast_files=unique_blast,
            reviewers=recommended_reviewers,
            bus_factor=overall_bus_factor,
            warnings=warnings,
        )

        return CodeOwnershipReport(
            target_files=unique_targets,
            blast_radius_files=unique_blast,
            file_ownerships=file_ownerships,
            recommended_reviewers=recommended_reviewers,
            overall_bus_factor=overall_bus_factor,
            knowledge_loss_warnings=warnings,
            summary=summary,
        )

    @classmethod
    def _analyze_file_ownership(
        cls,
        file_path: str,
        records: List[CommitChangeItem],
        ref_time: datetime,
        half_life_days: float,
    ) -> FileOwnership:
        """Calculate author breakdown and bus factor for a single file."""
        ref_time = _ensure_utc(ref_time)
        if not records:
            return FileOwnership(
                file_path=file_path,
                total_commits=0,
                ownership_level="DIFFUSED",
                bus_factor=1,
            )

        author_stats: Dict[Tuple[str, str], dict] = defaultdict(
            lambda: {
                "commits": 0,
                "insertions": 0,
                "deletions": 0,
                "raw_churn": 0,
                "decayed_churn": 0.0,
                "last_dt": None,
            }
        )

        for r in records:
            r_committed_at = _ensure_utc(r.committed_at)
            key = (r.author_name, r.author_email)
            stats = author_stats[key]
            stats["commits"] += 1
            stats["insertions"] += r.insertions
            stats["deletions"] += r.deletions

            churn = max(1, r.insertions + r.deletions)
            stats["raw_churn"] += churn

            # Half-life decay: w = 2^(-dt / tau)
            age_days = max(0.0, (ref_time - r_committed_at).total_seconds() / 86400.0)
            weight = 2.0 ** (-age_days / half_life_days)
            stats["decayed_churn"] += churn * weight

            if stats["last_dt"] is None or r_committed_at > stats["last_dt"]:
                stats["last_dt"] = r_committed_at

        total_decayed = sum(s["decayed_churn"] for s in author_stats.values())

        contributors: List[AuthorCommitStat] = []
        for (name, email), s in author_stats.items():
            pct = (s["decayed_churn"] / total_decayed * 100.0) if total_decayed > 0 else 0.0
            last_dt = s["last_dt"]
            days_ago = int((ref_time - last_dt).total_seconds() / 86400.0) if last_dt else None

            contributors.append(
                AuthorCommitStat(
                    author_name=name,
                    author_email=email,
                    commit_count=s["commits"],
                    lines_added=s["insertions"],
                    lines_deleted=s["deletions"],
                    raw_churn=s["raw_churn"],
                    decayed_churn=s["decayed_churn"],
                    ownership_percentage=pct,
                    last_committed_at=last_dt.isoformat() if last_dt else None,
                    days_since_last_commit=days_ago,
                )
            )

        # Sort by decayed churn descending
        contributors.sort(key=lambda c: c.decayed_churn, reverse=True)

        primary = contributors[0] if contributors else None
        co_owners = [c for c in contributors[1:] if c.ownership_percentage >= 15.0]

        # Ownership concentration level
        if primary and primary.ownership_percentage >= 70.0:
            level = "HIGH"
        elif primary and primary.ownership_percentage >= 40.0:
            level = "MEDIUM"
        else:
            level = "DIFFUSED"

        # File bus factor (authors needed for 75% decayed churn)
        decayed_dict = {(c.author_name, c.author_email): c.decayed_churn for c in contributors}
        bus_factor = cls._calculate_bus_factor(decayed_dict)

        return FileOwnership(
            file_path=file_path,
            total_commits=len(records),
            primary_owner=primary,
            co_owners=co_owners,
            all_contributors=contributors,
            ownership_level=level,
            bus_factor=bus_factor,
        )

    @classmethod
    def _calculate_bus_factor(cls, author_decayed: Dict[Tuple[str, str], float]) -> int:
        """Calculate bus factor: minimum authors whose combined share >= 75%."""
        if not author_decayed:
            return 1

        total = sum(author_decayed.values())
        if total <= 0:
            return 1

        sorted_shares = sorted(author_decayed.values(), reverse=True)
        running = 0.0
        count = 0
        threshold = 0.75 * total

        for share in sorted_shares:
            running += share
            count += 1
            if running >= threshold:
                break

        return max(1, count)

    @classmethod
    def _recommend_reviewers(
        cls,
        target_files: List[str],
        blast_radius_files: List[str],
        file_ownerships: List[FileOwnership],
        file_to_records: Dict[str, List[CommitChangeItem]],
        target_author_decayed: Dict[Tuple[str, str], float],
        blast_author_decayed: Dict[Tuple[str, str], float],
        author_last_active: Dict[Tuple[str, str], datetime],
        author_commit_counts: Dict[Tuple[str, str], int],
        current_author: Optional[str],
        ref_time: datetime,
    ) -> List[ReviewerRecommendation]:
        """Rank and qualify domain reviewers best positioned to inspect the change."""
        all_authors = set(target_author_decayed.keys()) | set(blast_author_decayed.keys())
        if not all_authors:
            return []

        clean_curr = current_author.strip().lower() if current_author else None

        total_target_churn = sum(target_author_decayed.values())
        total_blast_churn = sum(blast_author_decayed.values())

        # Map authors to files where they hold >= 25% ownership
        author_target_files: Dict[Tuple[str, str], List[str]] = defaultdict(list)
        author_blast_files: Dict[Tuple[str, str], List[str]] = defaultdict(list)

        for fo in file_ownerships:
            for contrib in fo.all_contributors:
                if contrib.ownership_percentage >= 25.0:
                    author_target_files[(contrib.author_name, contrib.author_email)].append(
                        fo.file_path
                    )

        for bf in blast_radius_files:
            b_recs = file_to_records.get(bf, [])
            if not b_recs:
                continue
            b_ownership = cls._analyze_file_ownership(
                file_path=bf,
                records=b_recs,
                ref_time=ref_time,
                half_life_days=cls.DEFAULT_HALF_LIFE_DAYS,
            )
            for contrib in b_ownership.all_contributors:
                if contrib.ownership_percentage >= 25.0:
                    author_blast_files[(contrib.author_name, contrib.author_email)].append(bf)

        candidates: List[ReviewerRecommendation] = []

        for auth_key in all_authors:
            name, email = auth_key
            # Exclude current author
            if clean_curr:
                if name.lower() == clean_curr or (email and email.lower() == clean_curr):
                    continue

            # 1. Target expertise (0.0 to 1.0)
            t_score = (
                (target_author_decayed[auth_key] / total_target_churn)
                if total_target_churn > 0
                else 0.0
            )

            # 2. Blast radius expertise (0.0 to 1.0)
            b_score = (
                (blast_author_decayed[auth_key] / total_blast_churn)
                if total_blast_churn > 0
                else 0.0
            )

            # 3. Recency score (0.1 to 1.0)
            last_dt = author_last_active.get(auth_key)
            days_ago = int((ref_time - last_dt).total_seconds() / 86400.0) if last_dt else 999
            if days_ago <= 30:
                r_score = 1.0
            elif days_ago <= 90:
                r_score = 0.75
            elif days_ago <= 180:
                r_score = 0.50
            elif days_ago <= 365:
                r_score = 0.25
            else:
                r_score = 0.10

            # Combined score
            if blast_radius_files:
                combined_score = 0.60 * t_score + 0.30 * b_score + 0.10 * r_score
            else:
                combined_score = 0.85 * t_score + 0.15 * r_score

            # Role classification
            owned_targets = author_target_files.get(auth_key, [])
            owned_blast = author_blast_files.get(auth_key, [])

            if t_score >= 0.40 or len(owned_targets) >= 1:
                role = "PRIMARY_OWNER"
            elif b_score >= 0.30 or (len(owned_blast) >= 1 and t_score < 0.20):
                role = "BLAST_RADIUS_GUARDIAN"
            else:
                role = "COMPONENT_EXPERT"

            # Formulate grounded rationale
            rec_count = author_commit_counts.get(auth_key, 0)
            rationale_parts = []
            if owned_targets:
                files_str = f"'{owned_targets[0]}'" + (
                    f" (+{len(owned_targets) - 1} more)" if len(owned_targets) > 1 else ""
                )
                rationale_parts.append(
                    f"Primary maintainer of target file {files_str} ({t_score * 100.0:.0f}% target churn)"
                )
            elif t_score > 0.15:
                rationale_parts.append(
                    f"Authored {t_score * 100.0:.0f}% of changes across modified targets"
                )

            if owned_blast:
                bf_str = f"'{owned_blast[0]}'" + (
                    f" (+{len(owned_blast) - 1} more)" if len(owned_blast) > 1 else ""
                )
                rationale_parts.append(f"Guardian of affected blast-radius caller {bf_str}")
            elif b_score > 0.15:
                rationale_parts.append(
                    f"Authored {b_score * 100.0:.0f}% of changes in affected callers"
                )

            if days_ago <= 30:
                rationale_parts.append(f"active {days_ago}d ago ({rec_count} commits)")
            elif days_ago <= 180:
                rationale_parts.append(f"last active {days_ago}d ago")
            else:
                rationale_parts.append(f"inactive for {days_ago}d")

            rationale = (
                "; ".join(rationale_parts)
                if rationale_parts
                else f"Contributed {rec_count} commits"
            )

            candidates.append(
                ReviewerRecommendation(
                    author_name=name,
                    author_email=email,
                    score=combined_score,
                    role=role,
                    rationale=rationale,
                    target_files_owned=owned_targets,
                    blast_radius_files_owned=owned_blast,
                    commits_count=rec_count,
                    days_since_last_commit=days_ago if days_ago < 999 else None,
                )
            )

        # Sort candidates by recommendation score descending
        candidates.sort(key=lambda c: c.score, reverse=True)
        return candidates[:5]

    @classmethod
    def _generate_summary(
        cls,
        target_files: List[str],
        blast_files: List[str],
        reviewers: List[ReviewerRecommendation],
        bus_factor: int,
        warnings: List[str],
    ) -> str:
        """Produce a high-signal human summary of ownership and recommendations."""
        rev_names = [f"{r.author_name} ({r.role})" for r in reviewers[:2]]
        rev_summary = (
            f"Recommended reviewers: {', '.join(rev_names)}."
            if rev_names
            else "No active reviewers identified."
        )

        risk_summary = f"Bus Factor: {bus_factor}."
        if warnings:
            risk_summary += f" {len(warnings)} ownership risk alert(s) flagged."

        return (
            f"Analyzed code ownership across {len(target_files)} target file(s) and {len(blast_files)} blast-radius file(s). "
            f"{risk_summary} {rev_summary}"
        )

    @classmethod
    async def query_and_analyze(
        cls,
        db: Any,
        repository_id: Any,
        target_files: List[str],
        blast_radius_files: Optional[List[str]] = None,
        current_author: Optional[str] = None,
        limit: int = 5000,
    ) -> CodeOwnershipReport:
        """
        Database loader: queries Commit and CommitFileChange rows for the specified files,
        then invokes pure deterministic analyze_ownership().
        """
        from sqlalchemy import select

        from app.models.commit import Commit
        from app.models.commit_file_change import CommitFileChange

        clean_targets = [_normalize_path(f) for f in target_files if f and f.strip()]
        clean_blast = [
            _normalize_path(f)
            for f in (blast_radius_files or [])
            if f and f.strip() and _normalize_path(f) not in clean_targets
        ]
        all_files = list(set(clean_targets) | set(clean_blast))

        if not all_files:
            return CodeOwnershipReport(
                target_files=clean_targets,
                blast_radius_files=clean_blast,
                summary="No files provided for ownership query.",
            )

        query = (
            select(
                Commit.commit_hash,
                Commit.author_name,
                Commit.author_email,
                Commit.committed_at,
                CommitFileChange.file_path,
                CommitFileChange.insertions,
                CommitFileChange.deletions,
            )
            .join(CommitFileChange, Commit.id == CommitFileChange.commit_id)
            .where(
                Commit.repository_id == repository_id,
                CommitFileChange.file_path.in_(all_files),
            )
            .order_by(Commit.committed_at.desc())
            .limit(limit)
        )
        res = await db.execute(query)
        rows = res.all()

        records = [
            CommitChangeItem(
                commit_hash=r[0],
                author_name=r[1],
                author_email=r[2],
                committed_at=r[3],
                file_path=_normalize_path(r[4]),
                insertions=r[5] or 0,
                deletions=r[6] or 0,
            )
            for r in rows
        ]

        return cls.analyze_ownership(
            target_files=clean_targets,
            blast_radius_files=clean_blast,
            commit_records=records,
            current_author=current_author,
        )
