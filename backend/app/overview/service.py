from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Set

from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.history.guarding_tests import (
    build_test_coverage_mapping,
    is_test_file,
    match_test_by_naming,
)
from app.models.commit import Commit
from app.models.commit_file_change import CommitFileChange
from app.models.dependency import CodeDependency
from app.models.design_constraint import DesignConstraint
from app.models.engineering_doc import EngineeringDocument
from app.models.issue import Issue
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.models.source_file import SourceFile
from app.models.symbol import Symbol
from app.schemas.repository import (
    HealthMetricDetail,
    HotspotFileItem,
    RepositoryHealthIndicators,
    RepositoryOverviewResponse,
    TopContributorItem,
)

logger = logging.getLogger(__name__)


def _infer_component_path(path: str) -> str:
    """Infer architectural component directory from file path."""
    parts = path.strip("/").split("/")
    if len(parts) <= 1:
        return "root"
    if len(parts) >= 3 and parts[0] in ["src", "app", "packages", "services", "libs"]:
        return f"{parts[0]}/{parts[1]}"
    return parts[0]


class RepositoryOverviewService:
    """
    Computes deterministic repository health indicators, structural statistics,
    defect hotspots, and ownership distribution from unified repository context.
    """

    @classmethod
    async def compute_overview(
        cls,
        db: AsyncSession,
        repository: Repository,
    ) -> RepositoryOverviewResponse:
        repo_id = repository.id

        # 1. Source files & languages
        files_stmt = select(SourceFile.path, SourceFile.language).where(
            SourceFile.repository_id == repo_id
        )
        files_rows = (await db.execute(files_stmt)).all()
        file_paths = [r[0] for r in files_rows]
        languages: Dict[str, int] = dict(Counter([r[1] for r in files_rows if r[1]]))

        # 2. Dependencies
        deps_stmt = select(CodeDependency.source_path, CodeDependency.target_path).where(
            CodeDependency.repository_id == repo_id
        )
        deps_rows = (await db.execute(deps_stmt)).all()
        dep_edges = [(r[0], r[1]) for r in deps_rows]
        dependency_count = len(dep_edges)

        # 3. Symbols & Architectural Roles
        symbol_count_stmt = (
            select(func.count()).select_from(Symbol).where(Symbol.repository_id == repo_id)
        )
        symbol_count = (await db.execute(symbol_count_stmt)).scalar() or 0

        roles_stmt = (
            select(Symbol.architectural_role, func.count())
            .where(Symbol.repository_id == repo_id, Symbol.architectural_role.is_not(None))
            .group_by(Symbol.architectural_role)
        )
        roles_rows = (await db.execute(roles_stmt)).all()
        dominant_roles: Dict[str, int] = {
            r[0].value if hasattr(r[0], "value") else str(r[0]): r[1]
            for r in roles_rows
            if r[0] is not None
        }

        # 4. Commits & Defect Fixes
        commits_stmt = select(
            Commit.id,
            Commit.author_name,
            Commit.author_email,
            Commit.is_defect_fix,
            Commit.committed_at,
        ).where(Commit.repository_id == repo_id)
        commits_rows = (await db.execute(commits_stmt)).all()
        commit_count = len(commits_rows)

        # 5. Pull Requests & Issues
        prs_stmt = select(PullRequest.id, PullRequest.state).where(
            PullRequest.repository_id == repo_id
        )
        prs_rows = (await db.execute(prs_stmt)).all()
        pull_request_count = len(prs_rows)
        open_pr_count = sum(1 for p in prs_rows if (p[1] or "").lower() == "open")

        issue_count_stmt = (
            select(func.count()).select_from(Issue).where(Issue.repository_id == repo_id)
        )
        issue_count = (await db.execute(issue_count_stmt)).scalar() or 0

        # 6. Engineering Governance Docs & Constraints
        adr_count_stmt = (
            select(func.count())
            .select_from(EngineeringDocument)
            .where(EngineeringDocument.repository_id == repo_id)
        )
        adr_count = (await db.execute(adr_count_stmt)).scalar() or 0

        constraint_count_stmt = (
            select(func.count())
            .select_from(DesignConstraint)
            .where(DesignConstraint.repository_id == repo_id)
        )
        constraint_count = (await db.execute(constraint_count_stmt)).scalar() or 0

        # 7. Hotspot Files (Changes & Defects)
        hotspots: List[HotspotFileItem] = []
        if commit_count > 0:
            hotspot_stmt = (
                select(
                    CommitFileChange.file_path,
                    func.count(CommitFileChange.id).label("change_count"),
                    func.sum(case((Commit.is_defect_fix.is_(True), 1), else_=0)).label(
                        "defect_count"
                    ),
                )
                .join(Commit, CommitFileChange.commit_id == Commit.id)
                .where(Commit.repository_id == repo_id)
                .group_by(CommitFileChange.file_path)
                .order_by(desc("change_count"))
                .limit(8)
            )
            hotspot_rows = (await db.execute(hotspot_stmt)).all()
            for r in hotspot_rows:
                f_path = r[0]
                c_cnt = int(r[1] or 0)
                d_cnt = int(r[2] or 0)
                if d_cnt >= 3 or (d_cnt >= 2 and c_cnt >= 5):
                    risk = "high"
                elif d_cnt >= 1 or c_cnt >= 4:
                    risk = "medium"
                else:
                    risk = "low"
                hotspots.append(
                    HotspotFileItem(
                        file_path=f_path,
                        change_count=c_cnt,
                        defect_count=d_cnt,
                        risk_level=risk,
                    )
                )

        # 8. Top Contributors & Ownership Blame
        top_contributors: List[TopContributorItem] = []
        now_utc = datetime.now(timezone.utc)
        if commit_count > 0:
            author_stats: Dict[str, Dict[str, Any]] = {}
            for row in commits_rows:
                name = row[1] or "Unknown"
                email = row[2] or ""
                committed_at = row[4]
                key = f"{name} <{email}>" if email else name
                if key not in author_stats:
                    author_stats[key] = {
                        "name": name,
                        "email": email,
                        "count": 0,
                        "latest": committed_at,
                    }
                author_stats[key]["count"] += 1
                if committed_at and (
                    not author_stats[key]["latest"] or committed_at > author_stats[key]["latest"]
                ):
                    author_stats[key]["latest"] = committed_at

            sorted_authors = sorted(author_stats.values(), key=lambda a: a["count"], reverse=True)
            for idx, a in enumerate(sorted_authors[:5]):
                pct = round((a["count"] / commit_count) * 100.0, 1)
                days_ago = None
                if a["latest"]:
                    dt = a["latest"]
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    days_ago = max(0, (now_utc - dt).days)

                role = (
                    "Lead Maintainer"
                    if idx == 0
                    else ("Core Contributor" if pct >= 20.0 else "Contributor")
                )
                top_contributors.append(
                    TopContributorItem(
                        name=a["name"],
                        email=a["email"],
                        commit_count=a["count"],
                        ownership_percentage=pct,
                        role=role,
                        days_since_last_commit=days_ago,
                    )
                )

        # 9. Compute 6 Health Dimensions

        # Dimension 1: Test Protection
        test_files = [p for p in file_paths if is_test_file(p)]
        source_files = [p for p in file_paths if not is_test_file(p)]
        covered_source_count = 0
        if source_files:
            coverage_map = build_test_coverage_mapping(
                set(source_files),
                dependency_edges=dep_edges,
                all_files=file_paths,
            )
            for sf in source_files:
                if coverage_map.get(sf):
                    covered_source_count += 1
                else:
                    for tf in test_files:
                        if match_test_by_naming(tf, sf):
                            covered_source_count += 1
                            break
            cov_ratio = covered_source_count / len(source_files)
            test_score = round(cov_ratio * 100.0, 1)
            if test_score >= 70.0:
                test_status = "healthy"
                test_summary = f"{test_score:.0f}% of source files protected by guarding test suites ({covered_source_count}/{len(source_files)} files)."
            elif test_score >= 40.0:
                test_status = "warning"
                test_summary = f"{test_score:.0f}% test coverage. {len(source_files) - covered_source_count} files lack direct test reachability."
            else:
                test_status = "alert"
                test_summary = f"Low test coverage ({test_score:.0f}%). Major verification gap detected across core files."
        else:
            test_score = 100.0
            cov_ratio = 1.0
            test_status = "healthy"
            test_summary = "No source files requiring test suites."

        test_metric = HealthMetricDetail(
            name="Test Protection",
            category="testing",
            score=test_score,
            status=test_status,
            summary=test_summary,
            details={
                "total_test_files": len(test_files),
                "total_source_files": len(source_files),
                "covered_source_files": covered_source_count,
                "untested_source_files": len(source_files) - covered_source_count,
                "coverage_ratio": round(cov_ratio, 2),
            },
        )

        # Dimension 2: Knowledge Distribution & Bus Factor
        if commit_count > 0:
            auth_counts = Counter(c[1] for c in commits_rows if c[1])
            sorted_auth = auth_counts.most_common()
            top_auth_name, top_auth_cnt = sorted_auth[0] if sorted_auth else ("Unknown", 0)
            top_share = top_auth_cnt / commit_count

            cum = 0
            bus_factor = 0
            for _, cnt in sorted_auth:
                cum += cnt
                bus_factor += 1
                if cum >= 0.75 * commit_count:
                    break
            bus_factor = max(1, bus_factor)

            if bus_factor >= 3:
                bus_score = 95.0
                bus_status = "healthy"
                bus_summary = f"Healthy knowledge distribution (Bus Factor: {bus_factor}, {len(sorted_auth)} contributors)."
            elif bus_factor == 2:
                bus_score = 75.0
                bus_status = "warning"
                bus_summary = f"Moderate knowledge concentration (Bus Factor: 2). Top author authored {top_share * 100:.0f}% of commits."
            else:
                bus_score = 50.0
                bus_status = "alert"
                bus_summary = f"Single-point-of-failure risk (Bus Factor: 1). {top_auth_name} authored {top_share * 100:.0f}% of commits."
        else:
            bus_score = 100.0
            bus_status = "healthy"
            bus_summary = "No commit blame recorded yet."
            bus_factor = 1
            top_share = 0.0

        bus_metric = HealthMetricDetail(
            name="Knowledge & Ownership",
            category="ownership",
            score=bus_score,
            status=bus_status,
            summary=bus_summary,
            details={
                "bus_factor": bus_factor,
                "contributor_count": len(top_contributors),
                "top_author_share": round(top_share, 2),
            },
        )

        # Dimension 3: Defect Pressure & Churn Stability
        defect_commits_cnt = sum(1 for c in commits_rows if c[3] is True)
        if commit_count > 0:
            defect_ratio = defect_commits_cnt / commit_count
            if defect_ratio <= 0.15:
                defect_score = 95.0
                defect_status = "healthy"
                defect_summary = f"Stable churn profile ({defect_commits_cnt}/{commit_count} defect repair commits, {defect_ratio * 100:.0f}%)."
            elif defect_ratio <= 0.30:
                defect_score = 75.0
                defect_status = "warning"
                defect_summary = f"Elevated defect repair frequency ({defect_commits_cnt}/{commit_count} commits, {defect_ratio * 100:.0f}%)."
            else:
                defect_score = 45.0
                defect_status = "alert"
                defect_summary = f"High defect pressure ({defect_commits_cnt}/{commit_count} commits, {defect_ratio * 100:.0f}%). Frequent regressions."
        else:
            defect_score = 100.0
            defect_status = "healthy"
            defect_summary = "No defect history recorded."
            defect_ratio = 0.0

        defect_metric = HealthMetricDetail(
            name="Defect Stability",
            category="stability",
            score=defect_score,
            status=defect_status,
            summary=defect_summary,
            details={
                "total_commits": commit_count,
                "defect_commits": defect_commits_cnt,
                "defect_ratio": round(defect_ratio, 2),
            },
        )

        # Dimension 4: Architectural Modularity
        density = dependency_count / max(1, len(file_paths))
        if len(file_paths) == 0:
            arch_score = 100.0
            arch_status = "healthy"
            arch_summary = "No architectural files indexed yet."
        elif density <= 8.0:
            arch_score = 90.0
            arch_status = "healthy"
            arch_summary = f"Clean architectural decoupling ({density:.1f} dependencies per file)."
        elif density <= 15.0:
            arch_score = 75.0
            arch_status = "warning"
            arch_summary = f"Moderate dependency coupling ({density:.1f} dependencies per file)."
        else:
            arch_score = 55.0
            arch_status = "alert"
            arch_summary = f"High structural coupling ({density:.1f} dependencies per file). Consider module separation."

        arch_metric = HealthMetricDetail(
            name="Architectural Modularity",
            category="architecture",
            score=arch_score,
            status=arch_status,
            summary=arch_summary,
            details={
                "coupling_density": round(density, 2),
                "dependency_count": dependency_count,
                "symbol_count": symbol_count,
                "classified_roles": dominant_roles,
            },
        )

        # Dimension 5: Engineering Governance
        if adr_count >= 2 or constraint_count >= 5:
            gov_score = 95.0
            gov_status = "healthy"
            gov_summary = f"Documented architecture ({adr_count} ADRs, {constraint_count} active design constraints)."
        elif adr_count >= 1 or constraint_count >= 1:
            gov_score = 75.0
            gov_status = "warning"
            gov_summary = f"Partial governance documentation ({adr_count} ADRs, {constraint_count} constraints)."
        else:
            gov_score = 50.0
            gov_status = "alert"
            gov_summary = "No architectural decision records (ADRs) or design constraints detected."

        gov_metric = HealthMetricDetail(
            name="Engineering Governance",
            category="governance",
            score=gov_score,
            status=gov_status,
            summary=gov_summary,
            details={
                "adr_count": adr_count,
                "constraint_count": constraint_count,
            },
        )

        # Dimension 6: Concurrent In-Flight Activity
        if open_pr_count == 0:
            act_score = 100.0
            act_status = "healthy"
            act_summary = "No conflicting in-flight branches. Clean merge environment."
        elif open_pr_count <= 3:
            act_score = 90.0
            act_status = "healthy"
            act_summary = f"{open_pr_count} open PRs in flight with low collision risk."
        elif open_pr_count <= 8:
            act_score = 75.0
            act_status = "warning"
            act_summary = (
                f"{open_pr_count} active PRs in progress. Monitor concurrent branch file changes."
            )
        else:
            act_score = 60.0
            act_status = "alert"
            act_summary = (
                f"High concurrency ({open_pr_count} active PRs). Elevated risk of merge collisions."
            )

        act_metric = HealthMetricDetail(
            name="Concurrent Activity",
            category="concurrency",
            score=act_score,
            status=act_status,
            summary=act_summary,
            details={
                "open_pr_count": open_pr_count,
            },
        )

        # Composite Score Calculation
        composite = round(
            0.25 * test_score
            + 0.20 * bus_score
            + 0.20 * defect_score
            + 0.15 * arch_score
            + 0.10 * gov_score
            + 0.10 * act_score,
            1,
        )

        if composite >= 75.0:
            comp_status = "healthy"
            comp_summary = f"Repository health is robust ({composite:.0f}/100) across test coverage, stability, and architecture."
        elif composite >= 50.0:
            comp_status = "stable"
            comp_summary = f"Repository health is stable ({composite:.0f}/100) with moderate attention needed on specific signals."
        else:
            comp_status = "attention_needed"
            comp_summary = f"Attention recommended ({composite:.0f}/100). Significant risks detected in testing, bus factor, or defect pressure."

        health_indicators = RepositoryHealthIndicators(
            composite_score=composite,
            status=comp_status,
            summary=comp_summary,
            metrics={
                "test_protection": test_metric,
                "knowledge_distribution": bus_metric,
                "defect_stability": defect_metric,
                "architectural_modularity": arch_metric,
                "governance": gov_metric,
                "concurrent_activity": act_metric,
            },
        )

        # Components & containers
        components_set: Set[str] = {_infer_component_path(p) for p in file_paths}
        component_count = len(components_set)
        # Approximate containers (top level folders or default 1)
        container_count = max(1, len({p.split("/")[0] for p in file_paths if "/" in p}))

        return RepositoryOverviewResponse(
            repository_id=repo_id,
            name=repository.name,
            owner=repository.owner,
            full_name=repository.full_name,
            default_branch=repository.default_branch,
            indexed_at=repository.indexed_at,
            file_count=len(file_paths),
            symbol_count=symbol_count,
            dependency_count=dependency_count,
            commit_count=commit_count,
            pull_request_count=pull_request_count,
            issue_count=issue_count,
            adr_count=adr_count,
            constraint_count=constraint_count,
            languages=languages,
            health=health_indicators,
            hotspots=hotspots,
            top_contributors=top_contributors,
            dominant_roles=dominant_roles,
            container_count=container_count,
            component_count=component_count,
        )
