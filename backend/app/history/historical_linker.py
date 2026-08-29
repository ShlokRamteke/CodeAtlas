from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.history.reference_extractor import ReferenceExtractor
from app.models.commit import Commit
from app.models.commit_file_change import CommitFileChange
from app.models.historical_link import (
    CommitIssueLink,
    CommitPullRequestLink,
    PullRequestIssueLink,
)
from app.models.issue import Issue, IssueState
from app.models.pull_request import PullRequest, PullRequestState


@dataclass
class ParsedPullRequest:
    number: int
    title: str
    body: Optional[str] = None
    state: str = "open"
    author: str = "Developer"
    merged_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    labels: List[str] = field(default_factory=list)
    html_url: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class ParsedIssue:
    number: int
    title: str
    body: Optional[str] = None
    state: str = "open"
    author: str = "Developer"
    closed_at: Optional[datetime] = None
    labels: List[str] = field(default_factory=list)
    html_url: Optional[str] = None
    created_at: Optional[datetime] = None


class HistoricalLinker:
    """
    Deterministic linker that establishes and resolves Code -> Commit -> PR -> Issue
    traceability relationships.
    """

    async def index_pull_requests(
        self,
        repository_id: uuid.UUID,
        parsed_prs: List[ParsedPullRequest],
        db: AsyncSession,
    ) -> int:
        """Persist pull requests and link them to issues and commits."""
        indexed_count = 0

        for pr_data in parsed_prs:
            # Check if PR already exists
            stmt = select(PullRequest).where(
                PullRequest.repository_id == repository_id,
                PullRequest.number == pr_data.number,
            )
            existing_pr = (await db.execute(stmt)).scalar_one_or_none()

            state_val = PullRequestState.OPEN
            pr_state_str = str(pr_data.state).lower()
            if pr_state_str == "merged" or pr_data.merged_at:
                state_val = PullRequestState.MERGED
            elif pr_state_str == "closed":
                state_val = PullRequestState.CLOSED

            if existing_pr:
                existing_pr.title = pr_data.title
                existing_pr.body = pr_data.body
                existing_pr.state = state_val
                existing_pr.author = pr_data.author
                existing_pr.merged_at = pr_data.merged_at
                existing_pr.closed_at = pr_data.closed_at
                existing_pr.labels = pr_data.labels
                existing_pr.html_url = pr_data.html_url
                pr_obj = existing_pr
            else:
                pr_obj = PullRequest(
                    id=uuid.uuid4(),
                    repository_id=repository_id,
                    number=pr_data.number,
                    title=pr_data.title,
                    body=pr_data.body,
                    state=state_val,
                    author=pr_data.author,
                    merged_at=pr_data.merged_at,
                    closed_at=pr_data.closed_at,
                    labels=pr_data.labels,
                    html_url=pr_data.html_url,
                )
                if pr_data.created_at:
                    pr_obj.created_at = pr_data.created_at
                db.add(pr_obj)
                indexed_count += 1

            await db.flush()

            # 1. Extract and store PR -> Issue links
            issue_refs = ReferenceExtractor.extract_from_pull_request(
                pr_obj.title, pr_obj.body
            )
            for iref in issue_refs:
                # Find matching Issue if already ingested
                issue_stmt = select(Issue).where(
                    Issue.repository_id == repository_id,
                    Issue.number == iref.issue_number,
                )
                matched_issue = (await db.execute(issue_stmt)).scalar_one_or_none()

                # Check if link already exists
                link_stmt = select(PullRequestIssueLink).where(
                    PullRequestIssueLink.pull_request_id == pr_obj.id,
                    PullRequestIssueLink.issue_number == iref.issue_number,
                )
                existing_link = (await db.execute(link_stmt)).scalar_one_or_none()
                if not existing_link:
                    link_obj = PullRequestIssueLink(
                        id=uuid.uuid4(),
                        pull_request_id=pr_obj.id,
                        issue_id=matched_issue.id if matched_issue else None,
                        issue_number=iref.issue_number,
                        link_type=iref.link_type,
                        raw_reference=iref.raw_match,
                        confidence=iref.confidence,
                    )
                    db.add(link_obj)

            # 2. Reconcile unlinked CommitPullRequestLinks that reference this PR number
            c_link_stmt = select(CommitPullRequestLink).where(
                CommitPullRequestLink.pr_number == pr_obj.number,
                CommitPullRequestLink.pull_request_id.is_(None),
            )
            unlinked_c_links = list((await db.execute(c_link_stmt)).scalars().all())
            for cl in unlinked_c_links:
                cl.pull_request_id = pr_obj.id

        await db.commit()
        return indexed_count

    async def index_issues(
        self,
        repository_id: uuid.UUID,
        parsed_issues: List[ParsedIssue],
        db: AsyncSession,
    ) -> int:
        """Persist issues and resolve unlinked references from commits and PRs."""
        indexed_count = 0

        for issue_data in parsed_issues:
            stmt = select(Issue).where(
                Issue.repository_id == repository_id,
                Issue.number == issue_data.number,
            )
            existing_issue = (await db.execute(stmt)).scalar_one_or_none()

            state_val = IssueState.OPEN
            issue_state_str = str(issue_data.state).lower()
            if issue_state_str == "closed" or issue_data.closed_at:
                state_val = IssueState.CLOSED

            if existing_issue:
                existing_issue.title = issue_data.title
                existing_issue.body = issue_data.body
                existing_issue.state = state_val
                existing_issue.author = issue_data.author
                existing_issue.closed_at = issue_data.closed_at
                existing_issue.labels = issue_data.labels
                existing_issue.html_url = issue_data.html_url
                issue_obj = existing_issue
            else:
                issue_obj = Issue(
                    id=uuid.uuid4(),
                    repository_id=repository_id,
                    number=issue_data.number,
                    title=issue_data.title,
                    body=issue_data.body,
                    state=state_val,
                    author=issue_data.author,
                    closed_at=issue_data.closed_at,
                    labels=issue_data.labels,
                    html_url=issue_data.html_url,
                )
                if issue_data.created_at:
                    issue_obj.created_at = issue_data.created_at
                db.add(issue_obj)
                indexed_count += 1

            await db.flush()

            # 1. Resolve unlinked CommitIssueLinks referencing this issue_number
            c_stmt = (
                select(CommitIssueLink)
                .join(Commit, CommitIssueLink.commit_id == Commit.id)
                .where(
                    Commit.repository_id == repository_id,
                    CommitIssueLink.issue_number == issue_obj.number,
                    CommitIssueLink.issue_id.is_(None),
                )
            )
            unlinked_c_links = list((await db.execute(c_stmt)).scalars().all())
            for cl in unlinked_c_links:
                cl.issue_id = issue_obj.id

            # 2. Resolve unlinked PullRequestIssueLinks referencing this issue_number
            pr_stmt = (
                select(PullRequestIssueLink)
                .join(PullRequest, PullRequestIssueLink.pull_request_id == PullRequest.id)
                .where(
                    PullRequest.repository_id == repository_id,
                    PullRequestIssueLink.issue_number == issue_obj.number,
                    PullRequestIssueLink.issue_id.is_(None),
                )
            )
            unlinked_pr_links = list((await db.execute(pr_stmt)).scalars().all())
            for pl in unlinked_pr_links:
                pl.issue_id = issue_obj.id

        await db.commit()
        return indexed_count

    async def link_commit(
        self,
        repository_id: uuid.UUID,
        commit: Commit,
        db: AsyncSession,
    ) -> Tuple[List[CommitPullRequestLink], List[CommitIssueLink]]:
        """
        Extract references from commit message and save CommitPullRequestLink & CommitIssueLink.
        """
        refs = ReferenceExtractor.extract_from_commit(commit.message)
        pr_links: List[CommitPullRequestLink] = []
        issue_links: List[CommitIssueLink] = []

        # 1. Handle PR links
        for pr_ref in refs.pull_requests:
            # Check if PR exists
            pr_stmt = select(PullRequest).where(
                PullRequest.repository_id == repository_id,
                PullRequest.number == pr_ref.pr_number,
            )
            matched_pr = (await db.execute(pr_stmt)).scalar_one_or_none()

            # Check if link exists
            link_stmt = select(CommitPullRequestLink).where(
                CommitPullRequestLink.commit_id == commit.id,
                CommitPullRequestLink.pr_number == pr_ref.pr_number,
            )
            existing_link = (await db.execute(link_stmt)).scalar_one_or_none()
            if not existing_link:
                link_obj = CommitPullRequestLink(
                    id=uuid.uuid4(),
                    commit_id=commit.id,
                    pull_request_id=matched_pr.id if matched_pr else None,
                    pr_number=pr_ref.pr_number,
                    link_type=pr_ref.link_type,
                    raw_reference=pr_ref.raw_match,
                    confidence=pr_ref.confidence,
                )
                db.add(link_obj)
                pr_links.append(link_obj)
            else:
                if matched_pr and not existing_link.pull_request_id:
                    existing_link.pull_request_id = matched_pr.id
                pr_links.append(existing_link)

        # 2. Handle Issue links
        for issue_ref in refs.issues:
            # Check if Issue exists
            issue_stmt = select(Issue).where(
                Issue.repository_id == repository_id,
                Issue.number == issue_ref.issue_number,
            )
            matched_issue = (await db.execute(issue_stmt)).scalar_one_or_none()

            # Check if link exists
            link_stmt = select(CommitIssueLink).where(
                CommitIssueLink.commit_id == commit.id,
                CommitIssueLink.issue_number == issue_ref.issue_number,
            )
            existing_link = (await db.execute(link_stmt)).scalar_one_or_none()
            if not existing_link:
                link_obj = CommitIssueLink(
                    id=uuid.uuid4(),
                    commit_id=commit.id,
                    issue_id=matched_issue.id if matched_issue else None,
                    issue_number=issue_ref.issue_number,
                    link_type=issue_ref.link_type,
                    raw_reference=issue_ref.raw_match,
                    confidence=issue_ref.confidence,
                )
                db.add(link_obj)
                issue_links.append(link_obj)
            else:
                if matched_issue and not existing_link.issue_id:
                    existing_link.issue_id = matched_issue.id
                issue_links.append(existing_link)

        return pr_links, issue_links

    async def get_historical_trace(
        self,
        repository_id: uuid.UUID,
        file_path: str,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Trace the full historical chain for a given file:
        Code / File -> Commit -> Pull Request -> Issue.
        """
        # Fetch commits touching file_path or directory prefix
        norm_path = file_path.strip("/")
        stmt = (
            select(Commit, CommitFileChange)
            .join(CommitFileChange, Commit.id == CommitFileChange.commit_id)
            .where(
                Commit.repository_id == repository_id,
                or_(
                    CommitFileChange.file_path == file_path,
                    CommitFileChange.file_path == norm_path,
                    CommitFileChange.file_path.startswith(f"{norm_path}/"),
                ),
            )
            .order_by(Commit.committed_at.desc())
        )
        rows = (await db.execute(stmt)).all()

        trace_chain: List[Dict[str, Any]] = []
        seen_prs: Dict[int, Dict[str, Any]] = {}
        seen_issues: Dict[int, Dict[str, Any]] = {}

        for commit, change in rows:
            # Get linked PRs for this commit
            pr_links_stmt = select(CommitPullRequestLink).where(
                CommitPullRequestLink.commit_id == commit.id
            )
            pr_links = list((await db.execute(pr_links_stmt)).scalars().all())

            # Get linked issues directly for this commit
            issue_links_stmt = select(CommitIssueLink).where(
                CommitIssueLink.commit_id == commit.id
            )
            issue_links = list((await db.execute(issue_links_stmt)).scalars().all())

            linked_prs_data: List[Dict[str, Any]] = []
            for pl in pr_links:
                pr_detail: Optional[PullRequest] = None
                if pl.pull_request_id:
                    pr_detail = await db.get(PullRequest, pl.pull_request_id)
                elif pl.pr_number:
                    pr_stmt = select(PullRequest).where(
                        PullRequest.repository_id == repository_id,
                        PullRequest.number == pl.pr_number,
                    )
                    pr_detail = (await db.execute(pr_stmt)).scalar_one_or_none()

                # Get PR's linked issues
                pr_issue_links: List[Dict[str, Any]] = []
                if pr_detail:
                    pr_issues_stmt = select(PullRequestIssueLink).where(
                        PullRequestIssueLink.pull_request_id == pr_detail.id
                    )
                    pil_rows = list((await db.execute(pr_issues_stmt)).scalars().all())
                    for pil in pil_rows:
                        iss_obj = await db.get(Issue, pil.issue_id) if pil.issue_id else None
                        iss_dict = {
                            "number": pil.issue_number,
                            "title": iss_obj.title if iss_obj else f"Issue #{pil.issue_number}",
                            "state": iss_obj.state.value if iss_obj else "unknown",
                            "link_type": pil.link_type,
                            "labels": iss_obj.labels if iss_obj else [],
                            "html_url": iss_obj.html_url if iss_obj else None,
                        }
                        pr_issue_links.append(iss_dict)
                        seen_issues[pil.issue_number] = iss_dict

                pr_item = {
                    "number": pl.pr_number,
                    "title": pr_detail.title if pr_detail else f"Pull Request #{pl.pr_number}",
                    "state": pr_detail.state.value if pr_detail else "unknown",
                    "author": pr_detail.author if pr_detail else "Unknown",
                    "link_type": pl.link_type,
                    "merged_at": pr_detail.merged_at.isoformat() if pr_detail and pr_detail.merged_at else None,
                    "labels": pr_detail.labels if pr_detail else [],
                    "html_url": pr_detail.html_url if pr_detail else None,
                    "linked_issues": pr_issue_links,
                }
                linked_prs_data.append(pr_item)
                seen_prs[pl.pr_number] = pr_item

            linked_issues_data: List[Dict[str, Any]] = []
            for il in issue_links:
                iss_detail: Optional[Issue] = None
                if il.issue_id:
                    iss_detail = await db.get(Issue, il.issue_id)
                elif il.issue_number:
                    iss_stmt = select(Issue).where(
                        Issue.repository_id == repository_id,
                        Issue.number == il.issue_number,
                    )
                    iss_detail = (await db.execute(iss_stmt)).scalar_one_or_none()

                iss_item = {
                    "number": il.issue_number,
                    "title": iss_detail.title if iss_detail else f"Issue #{il.issue_number}",
                    "state": iss_detail.state.value if iss_detail else "unknown",
                    "author": iss_detail.author if iss_detail else "Unknown",
                    "link_type": il.link_type,
                    "labels": iss_detail.labels if iss_detail else [],
                    "html_url": iss_detail.html_url if iss_detail else None,
                }
                linked_issues_data.append(iss_item)
                seen_issues[il.issue_number] = iss_item

            trace_chain.append({
                "commit_hash": commit.commit_hash,
                "author_name": commit.author_name,
                "committed_at": commit.committed_at.isoformat(),
                "message": commit.message,
                "change_type": change.change_type.value,
                "insertions": change.insertions,
                "deletions": change.deletions,
                "linked_pull_requests": linked_prs_data,
                "linked_issues": linked_issues_data,
            })

        return {
            "file_path": file_path,
            "total_commits": len(trace_chain),
            "total_pull_requests": len(seen_prs),
            "total_issues": len(seen_issues),
            "trace_chain": trace_chain,
            "all_pull_requests": list(seen_prs.values()),
            "all_issues": list(seen_issues.values()),
        }

    @staticmethod
    def parse_synthetic_prs(payload: List[Dict[str, Any]]) -> List[ParsedPullRequest]:
        """Convert JSON pull requests payload to ParsedPullRequest list."""
        parsed: List[ParsedPullRequest] = []
        for item in payload:
            raw_merged = item.get("merged_at")
            merged_at = None
            if raw_merged:
                try:
                    merged_at = datetime.fromisoformat(str(raw_merged).replace("Z", "+00:00"))
                except Exception:
                    merged_at = datetime.now(timezone.utc)

            raw_closed = item.get("closed_at")
            closed_at = None
            if raw_closed:
                try:
                    closed_at = datetime.fromisoformat(str(raw_closed).replace("Z", "+00:00"))
                except Exception:
                    closed_at = None

            raw_created = item.get("created_at")
            created_at = None
            if raw_created:
                try:
                    created_at = datetime.fromisoformat(str(raw_created).replace("Z", "+00:00"))
                except Exception:
                    created_at = None

            parsed.append(
                ParsedPullRequest(
                    number=int(item.get("number", 0)),
                    title=item.get("title", ""),
                    body=item.get("body"),
                    state=str(item.get("state", "open")).lower(),
                    author=item.get("author") or item.get("user", {}).get("login") or "Developer",
                    merged_at=merged_at,
                    closed_at=closed_at,
                    labels=item.get("labels", []),
                    html_url=item.get("html_url"),
                    created_at=created_at,
                )
            )
        return parsed

    @staticmethod
    def parse_synthetic_issues(payload: List[Dict[str, Any]]) -> List[ParsedIssue]:
        """Convert JSON issues payload to ParsedIssue list."""
        parsed: List[ParsedIssue] = []
        for item in payload:
            raw_closed = item.get("closed_at")
            closed_at = None
            if raw_closed:
                try:
                    closed_at = datetime.fromisoformat(str(raw_closed).replace("Z", "+00:00"))
                except Exception:
                    closed_at = None

            raw_created = item.get("created_at")
            created_at = None
            if raw_created:
                try:
                    created_at = datetime.fromisoformat(str(raw_created).replace("Z", "+00:00"))
                except Exception:
                    created_at = None

            parsed.append(
                ParsedIssue(
                    number=int(item.get("number", 0)),
                    title=item.get("title", ""),
                    body=item.get("body"),
                    state=str(item.get("state", "open")).lower(),
                    author=item.get("author") or item.get("user", {}).get("login") or "Developer",
                    closed_at=closed_at,
                    labels=item.get("labels", []),
                    html_url=item.get("html_url"),
                    created_at=created_at,
                )
            )
        return parsed
