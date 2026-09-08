from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import String, cast, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commit import Commit
from app.models.commit_file_change import CommitFileChange
from app.models.issue import Issue, IssueState
from app.models.pull_request import PullRequest, PullRequestState
from app.models.source_file import SourceFile
from app.models.symbol import Symbol
from app.schemas.history import (
    HistoricalEvidenceItem,
    HistoricalRetrievalRequest,
    HistoricalRetrievalResponse,
    SymbolHistoryResponse,
)


class HistoricalRetriever:
    """
    Deterministic Historical Retrieval Engine.
    Provides multi-dimensional searching across commits, pull requests, and issues,
    and extracts ranked historical evidence without invoking an LLM.
    """

    async def search_commits(
        self,
        repository_id: uuid.UUID,
        db: AsyncSession,
        query: Optional[str] = None,
        author: Optional[str] = None,
        file_path: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Commit]:
        """Search commits by message keyword, author name/email, touched file path, and date range."""
        stmt = select(Commit).where(Commit.repository_id == repository_id)

        if file_path:
            clean_path = file_path.strip().strip("/")
            stmt = stmt.join(CommitFileChange, Commit.id == CommitFileChange.commit_id).where(
                or_(
                    CommitFileChange.file_path == clean_path,
                    CommitFileChange.file_path.ilike(f"{clean_path}/%"),
                )
            )

        if query:
            q_clean = query.strip()
            stmt = stmt.where(
                or_(
                    Commit.message.ilike(f"%{q_clean}%"),
                    Commit.commit_hash.ilike(f"{q_clean}%"),
                )
            )

        if author:
            a_clean = author.strip()
            stmt = stmt.where(
                or_(
                    Commit.author_name.ilike(f"%{a_clean}%"),
                    Commit.author_email.ilike(f"%{a_clean}%"),
                )
            )

        if since:
            stmt = stmt.where(Commit.committed_at >= since)

        if until:
            stmt = stmt.where(Commit.committed_at <= until)

        stmt = stmt.distinct().order_by(Commit.committed_at.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def search_pull_requests(
        self,
        repository_id: uuid.UUID,
        db: AsyncSession,
        query: Optional[str] = None,
        state: Optional[str] = None,
        author: Optional[str] = None,
        label: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[PullRequest]:
        """Search pull requests by keyword, status, author, label, and date range."""
        stmt = select(PullRequest).where(PullRequest.repository_id == repository_id)

        if query:
            q_clean = query.strip()
            num_clean = q_clean.lstrip("#")
            if num_clean.isdigit():
                stmt = stmt.where(
                    or_(
                        PullRequest.number == int(num_clean),
                        PullRequest.title.ilike(f"%{q_clean}%"),
                        PullRequest.body.ilike(f"%{q_clean}%"),
                    )
                )
            else:
                stmt = stmt.where(
                    or_(
                        PullRequest.title.ilike(f"%{q_clean}%"),
                        PullRequest.body.ilike(f"%{q_clean}%"),
                    )
                )

        if state:
            state_val = state.strip().lower()
            try:
                pr_state = PullRequestState(state_val)
                stmt = stmt.where(PullRequest.state == pr_state)
            except ValueError:
                pass

        if author:
            stmt = stmt.where(PullRequest.author.ilike(f"%{author.strip()}%"))

        if label:
            # Check JSON labels array via text casting
            stmt = stmt.where(cast(PullRequest.labels, String).ilike(f"%{label.strip()}%"))

        if since:
            stmt = stmt.where(PullRequest.created_at >= since)

        if until:
            stmt = stmt.where(PullRequest.created_at <= until)

        stmt = stmt.order_by(PullRequest.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def search_issues(
        self,
        repository_id: uuid.UUID,
        db: AsyncSession,
        query: Optional[str] = None,
        state: Optional[str] = None,
        author: Optional[str] = None,
        label: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Issue]:
        """Search issues by keyword, status, author, label, and date range."""
        stmt = select(Issue).where(Issue.repository_id == repository_id)

        if query:
            q_clean = query.strip()
            num_clean = q_clean.lstrip("#")
            if num_clean.isdigit():
                stmt = stmt.where(
                    or_(
                        Issue.number == int(num_clean),
                        Issue.title.ilike(f"%{q_clean}%"),
                        Issue.body.ilike(f"%{q_clean}%"),
                    )
                )
            else:
                stmt = stmt.where(
                    or_(
                        Issue.title.ilike(f"%{q_clean}%"),
                        Issue.body.ilike(f"%{q_clean}%"),
                    )
                )

        if state:
            state_val = state.strip().lower()
            try:
                iss_state = IssueState(state_val)
                stmt = stmt.where(Issue.state == iss_state)
            except ValueError:
                pass

        if author:
            stmt = stmt.where(Issue.author.ilike(f"%{author.strip()}%"))

        if label:
            stmt = stmt.where(cast(Issue.labels, String).ilike(f"%{label.strip()}%"))

        if since:
            stmt = stmt.where(Issue.created_at >= since)

        if until:
            stmt = stmt.where(Issue.created_at <= until)

        stmt = stmt.order_by(Issue.created_at.desc()).offset(offset).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def retrieve_symbol_history(
        self,
        repository_id: uuid.UUID,
        symbol_name: str,
        db: AsyncSession,
        file_path: Optional[str] = None,
        limit: int = 50,
    ) -> Optional[SymbolHistoryResponse]:
        """
        Find historical change events and provenance scoped to a specific symbol.
        """
        sym_query = (
            select(Symbol, SourceFile.path)
            .join(SourceFile, Symbol.file_id == SourceFile.id)
            .where(
                Symbol.repository_id == repository_id,
                Symbol.name == symbol_name,
            )
        )
        if file_path:
            sym_query = sym_query.where(SourceFile.path == file_path.strip().strip("/"))

        sym_result = (await db.execute(sym_query)).first()

        target_file_path: str
        line_start: Optional[int] = None
        line_end: Optional[int] = None

        if sym_result:
            sym_obj, f_path = sym_result
            target_file_path = f_path
            line_start = sym_obj.line_start
            line_end = sym_obj.line_end
        elif file_path:
            target_file_path = file_path.strip().strip("/")
        else:
            return None

        # Fetch commits touching this file
        commit_stmt = (
            select(Commit, CommitFileChange)
            .join(CommitFileChange, Commit.id == CommitFileChange.commit_id)
            .where(
                Commit.repository_id == repository_id,
                CommitFileChange.file_path == target_file_path,
            )
            .order_by(Commit.committed_at.asc())
        )
        commit_rows = (await db.execute(commit_stmt)).all()

        if not commit_rows:
            return SymbolHistoryResponse(
                symbol_name=symbol_name,
                file_path=target_file_path,
                line_start=line_start,
                line_end=line_end,
                introducing_commit=None,
                total_commits=0,
                commits=[],
                linked_pull_requests=[],
                linked_issues=[],
                evolution_timeline=[],
            )

        # Identify introducing commit
        introducing_commit: Optional[Dict[str, Any]] = None
        for c, fc in commit_rows:
            if fc.change_type == "added":
                introducing_commit = {
                    "commit_hash": c.commit_hash,
                    "author_name": c.author_name,
                    "committed_at": c.committed_at.isoformat(),
                    "message": c.message,
                }
                break
        if not introducing_commit and commit_rows:
            earliest_c, _ = commit_rows[0]
            introducing_commit = {
                "commit_hash": earliest_c.commit_hash,
                "author_name": earliest_c.author_name,
                "committed_at": earliest_c.committed_at.isoformat(),
                "message": earliest_c.message,
            }

        # Build list of relevant commits (those explicitly naming symbol or modifying file)
        commit_items: List[Dict[str, Any]] = []
        timeline_events: List[Dict[str, Any]] = []
        seen_hashes = set()
        all_linked_prs: Dict[int, Dict[str, Any]] = {}
        all_linked_issues: Dict[int, Dict[str, Any]] = {}

        for c, fc in reversed(commit_rows):
            if c.commit_hash in seen_hashes:
                continue
            seen_hashes.add(c.commit_hash)

            is_intro = introducing_commit and c.commit_hash == introducing_commit.get("commit_hash")
            mentions_symbol = symbol_name.lower() in c.message.lower()

            event_type = (
                "introduction"
                if is_intro
                else ("symbol_modification" if mentions_symbol else "file_modification")
            )

            # Pull PR links
            pr_links = []
            for pl in getattr(c, "pull_request_links", []):
                pr_dict = {
                    "pr_number": pl.pr_number,
                    "link_type": pl.link_type,
                    "confidence": pl.confidence,
                }
                pr_links.append(pr_dict)
                all_linked_prs[pl.pr_number] = pr_dict

            # Pull Issue links
            iss_links = []
            for il in getattr(c, "issue_links", []):
                iss_dict = {
                    "issue_number": il.issue_number,
                    "link_type": il.link_type,
                    "confidence": il.confidence,
                }
                iss_links.append(iss_dict)
                all_linked_issues[il.issue_number] = iss_dict

            commit_dict = {
                "commit_hash": c.commit_hash,
                "author_name": c.author_name,
                "committed_at": c.committed_at.isoformat(),
                "message": c.message,
                "change_type": fc.change_type,
                "insertions": fc.insertions,
                "deletions": fc.deletions,
                "mentions_symbol": mentions_symbol,
                "linked_pull_requests": pr_links,
                "linked_issues": iss_links,
            }
            commit_items.append(commit_dict)

            timeline_events.append(
                {
                    "event_type": event_type,
                    "timestamp": c.committed_at.isoformat(),
                    "commit_hash": c.commit_hash,
                    "author": c.author_name,
                    "summary": c.message.splitlines()[0] if c.message else "",
                    "linked_prs": [pl["pr_number"] for pl in pr_links],
                    "linked_issues": [il["issue_number"] for il in iss_links],
                }
            )

            if len(commit_items) >= limit:
                break

        return SymbolHistoryResponse(
            symbol_name=symbol_name,
            file_path=target_file_path,
            line_start=line_start,
            line_end=line_end,
            introducing_commit=introducing_commit,
            total_commits=len(commit_rows),
            commits=commit_items,
            linked_pull_requests=list(all_linked_prs.values()),
            linked_issues=list(all_linked_issues.values()),
            evolution_timeline=timeline_events,
        )

    async def retrieve_historical_evidence(
        self,
        repository_id: uuid.UUID,
        req: HistoricalRetrievalRequest,
        db: AsyncSession,
    ) -> HistoricalRetrievalResponse:
        """
        Synthesizes ranked deterministic historical evidence items from commits, PRs, and issues.
        """
        source_types = set(req.source_types or ["commit", "pull_request", "issue"])
        target_path = req.file_path or req.component_path

        evidence_items: List[HistoricalEvidenceItem] = []
        scope_info: Dict[str, Any] = {
            "query": req.query,
            "component_path": req.component_path,
            "file_path": req.file_path,
            "symbol_name": req.symbol_name,
            "author": req.author,
            "since": req.since.isoformat() if req.since else None,
            "until": req.until.isoformat() if req.until else None,
            "source_types": list(source_types),
        }

        # 1. Retrieve commits
        if "commit" in source_types:
            commits = await self.search_commits(
                repository_id=repository_id,
                db=db,
                query=req.query,
                author=req.author,
                file_path=target_path,
                since=req.since,
                until=req.until,
                limit=req.limit * 2,
            )

            for c in commits:
                score = 0.5
                citations = [f"commit:{c.commit_hash[:7]}"]

                # Extra relevance boosts
                if req.query and req.query.lower() in c.message.lower():
                    score += 0.3
                if req.symbol_name and req.symbol_name.lower() in c.message.lower():
                    score += 0.4
                if target_path and any(
                    target_path in fc.file_path for fc in getattr(c, "file_changes", [])
                ):
                    score += 0.2

                # Linked citations
                for pl in getattr(c, "pull_request_links", []):
                    citations.append(f"pr:#{pl.pr_number}")
                for il in getattr(c, "issue_links", []):
                    citations.append(f"issue:#{il.issue_number}")

                files_touched = [fc.file_path for fc in getattr(c, "file_changes", [])[:5]]
                snippet_text = c.message
                if files_touched:
                    snippet_text += f"\nFiles: {', '.join(files_touched)}"

                evidence_items.append(
                    HistoricalEvidenceItem(
                        id=f"ev_commit_{c.id}",
                        source_type="commit",
                        source_id=c.commit_hash,
                        title=f"Commit {c.commit_hash[:7]}: {c.message.splitlines()[0] if c.message else ''}",
                        snippet=snippet_text,
                        author=c.author_name,
                        timestamp=c.committed_at,
                        confidence=1.0,
                        score=min(round(score, 2), 1.0),
                        metadata={
                            "commit_hash": c.commit_hash,
                            "files_changed_count": c.files_changed_count,
                            "insertions": c.insertions,
                            "deletions": c.deletions,
                            "parent_hashes": c.parent_hashes or [],
                        },
                        citations=citations,
                    )
                )

        # 2. Retrieve Pull Requests
        if "pull_request" in source_types:
            prs = await self.search_pull_requests(
                repository_id=repository_id,
                db=db,
                query=req.query,
                author=req.author,
                since=req.since,
                until=req.until,
                limit=req.limit * 2,
            )

            for pr in prs:
                score = 0.5
                citations = [f"pr:#{pr.number}"]
                if req.query and (
                    req.query.lower() in pr.title.lower()
                    or (pr.body and req.query.lower() in pr.body.lower())
                ):
                    score += 0.3
                if req.symbol_name and (
                    req.symbol_name.lower() in pr.title.lower()
                    or (pr.body and req.symbol_name.lower() in pr.body.lower())
                ):
                    score += 0.4

                for cl in getattr(pr, "commit_links", []):
                    citations.append(f"commit:{cl.commit_id}")
                for il in getattr(pr, "issue_links", []):
                    citations.append(f"issue:#{il.issue_number}")

                snippet = pr.body[:400] if pr.body else "No description provided."

                evidence_items.append(
                    HistoricalEvidenceItem(
                        id=f"ev_pr_{pr.id}",
                        source_type="pull_request",
                        source_id=str(pr.number),
                        title=f"PR #{pr.number}: {pr.title} [{pr.state.value}]",
                        snippet=snippet,
                        author=pr.author,
                        timestamp=pr.merged_at or pr.closed_at or pr.created_at,
                        confidence=1.0,
                        score=min(round(score, 2), 1.0),
                        metadata={
                            "pr_number": pr.number,
                            "state": pr.state.value,
                            "labels": pr.labels or [],
                            "html_url": pr.html_url,
                        },
                        citations=citations,
                    )
                )

        # 3. Retrieve Issues
        if "issue" in source_types:
            issues = await self.search_issues(
                repository_id=repository_id,
                db=db,
                query=req.query,
                author=req.author,
                since=req.since,
                until=req.until,
                limit=req.limit * 2,
            )

            for iss in issues:
                score = 0.5
                citations = [f"issue:#{iss.number}"]
                if req.query and (
                    req.query.lower() in iss.title.lower()
                    or (iss.body and req.query.lower() in iss.body.lower())
                ):
                    score += 0.3
                if req.symbol_name and (
                    req.symbol_name.lower() in iss.title.lower()
                    or (iss.body and req.symbol_name.lower() in iss.body.lower())
                ):
                    score += 0.4

                for pil in getattr(iss, "pull_request_links", []):
                    citations.append(f"pr:#{pil.pull_request_id}")
                for cl in getattr(iss, "commit_links", []):
                    citations.append(f"commit:{cl.commit_id}")

                snippet = iss.body[:400] if iss.body else "No description provided."

                evidence_items.append(
                    HistoricalEvidenceItem(
                        id=f"ev_issue_{iss.id}",
                        source_type="issue",
                        source_id=str(iss.number),
                        title=f"Issue #{iss.number}: {iss.title} [{iss.state.value}]",
                        snippet=snippet,
                        author=iss.author,
                        timestamp=iss.closed_at or iss.created_at,
                        confidence=1.0,
                        score=min(round(score, 2), 1.0),
                        metadata={
                            "issue_number": iss.number,
                            "state": iss.state.value,
                            "labels": iss.labels or [],
                            "html_url": iss.html_url,
                        },
                        citations=citations,
                    )
                )

        # Sort evidence items by score desc, then timestamp desc
        evidence_items.sort(
            key=lambda e: (e.score, e.timestamp or datetime.min),
            reverse=True,
        )

        ranked_evidence = evidence_items[: req.limit]

        # Generate deterministic summary
        summary_lines = [
            f"Found {len(ranked_evidence)} historical evidence records for query scope."
        ]
        if req.symbol_name:
            summary_lines.append(f"Target symbol: `{req.symbol_name}`.")
        if target_path:
            summary_lines.append(f"Target path: `{target_path}`.")
        if req.query:
            summary_lines.append(f"Search keyword: '{req.query}'.")

        commit_count = sum(1 for e in ranked_evidence if e.source_type == "commit")
        pr_count = sum(1 for e in ranked_evidence if e.source_type == "pull_request")
        issue_count = sum(1 for e in ranked_evidence if e.source_type == "issue")
        summary_lines.append(
            f"Evidence breakdown: {commit_count} commits, {pr_count} pull requests, {issue_count} issues."
        )

        return HistoricalRetrievalResponse(
            repository_id=repository_id,
            query=req.query,
            scope=scope_info,
            total_evidence_count=len(evidence_items),
            evidence=ranked_evidence,
            summary=" ".join(summary_lines),
        )
