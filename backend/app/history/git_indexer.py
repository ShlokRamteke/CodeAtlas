from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commit import Commit
from app.models.commit_file_change import ChangeType, CommitFileChange


@dataclass
class ParsedFileChange:
    file_path: str
    change_type: ChangeType = ChangeType.MODIFIED
    insertions: int = 0
    deletions: int = 0
    old_path: Optional[str] = None


@dataclass
class ParsedCommit:
    commit_hash: str
    author_name: str
    author_email: str
    committed_at: datetime
    message: str
    parent_hashes: List[str] = field(default_factory=list)
    file_changes: List[ParsedFileChange] = field(default_factory=list)
    insertions: int = 0
    deletions: int = 0


@dataclass
class FileHistoryResult:
    file_path: str
    total_commits: int
    introducing_commit: Optional[Dict[str, Any]]
    commits: List[Dict[str, Any]]
    authors: List[Dict[str, Any]]


class GitHistoryIndexer:
    """Deterministic Git history parser, indexer, and file timeline analyzer."""

    async def index_commits(
        self,
        repository_id: uuid.UUID,
        parsed_commits: List[ParsedCommit],
        db: AsyncSession,
    ) -> int:
        """Persist commits and their file changes idempotently."""
        indexed_count = 0
        for pc in parsed_commits:
            # Check if commit already exists
            existing_stmt = select(Commit).where(
                Commit.repository_id == repository_id,
                Commit.commit_hash == pc.commit_hash,
            )
            existing = (await db.execute(existing_stmt)).scalar_one_or_none()
            if existing:
                # Backfill file changes & diff metrics if missing
                if (existing.files_changed_count == 0 or existing.insertions == 0) and pc.file_changes:
                    insertions = sum(fc.insertions for fc in pc.file_changes) or pc.insertions
                    deletions = sum(fc.deletions for fc in pc.file_changes) or pc.deletions
                    existing.files_changed_count = len(pc.file_changes)
                    existing.insertions = insertions
                    existing.deletions = deletions
                    for fc in pc.file_changes:
                        change_obj = CommitFileChange(
                            id=uuid.uuid4(),
                            commit_id=existing.id,
                            file_path=fc.file_path,
                            change_type=fc.change_type,
                            insertions=fc.insertions,
                            deletions=fc.deletions,
                            old_path=fc.old_path,
                        )
                        db.add(change_obj)
                    indexed_count += 1
                continue


            insertions = sum(fc.insertions for fc in pc.file_changes)
            deletions = sum(fc.deletions for fc in pc.file_changes)

            commit_obj = Commit(
                id=uuid.uuid4(),
                repository_id=repository_id,
                commit_hash=pc.commit_hash,
                author_name=pc.author_name,
                author_email=pc.author_email,
                committed_at=pc.committed_at,
                message=pc.message,
                parent_hashes=pc.parent_hashes,
                files_changed_count=len(pc.file_changes),
                insertions=insertions,
                deletions=deletions,
            )
            db.add(commit_obj)
            await db.flush()

            for fc in pc.file_changes:
                change_obj = CommitFileChange(
                    id=uuid.uuid4(),
                    commit_id=commit_obj.id,
                    file_path=fc.file_path,
                    change_type=fc.change_type,
                    insertions=fc.insertions,
                    deletions=fc.deletions,
                    old_path=fc.old_path,
                )
                db.add(change_obj)

            # Extract and persist PR & Issue links for this commit
            from app.history.historical_linker import HistoricalLinker

            linker = HistoricalLinker()
            await linker.link_commit(repository_id, commit_obj, db)

            indexed_count += 1

        await db.commit()
        return indexed_count

    async def get_file_history(
        self,
        repository_id: uuid.UUID,
        file_path: str,
        db: AsyncSession,
    ) -> FileHistoryResult:
        """Retrieve chronological commit timeline for a file and find introducing commit."""
        stmt = (
            select(Commit, CommitFileChange)
            .join(CommitFileChange, Commit.id == CommitFileChange.commit_id)
            .where(
                Commit.repository_id == repository_id,
                CommitFileChange.file_path == file_path,
            )
            .order_by(Commit.committed_at.desc())
        )
        rows = (await db.execute(stmt)).all()

        commits_data: List[Dict[str, Any]] = []
        authors_map: Dict[str, Dict[str, Any]] = {}

        introducing_commit: Optional[Dict[str, Any]] = None

        for commit, change in rows:
            linked_prs = [
                {
                    "pr_number": pl.pr_number,
                    "link_type": pl.link_type,
                    "raw_reference": pl.raw_reference,
                }
                for pl in getattr(commit, "pull_request_links", [])
            ]
            linked_issues = [
                {
                    "issue_number": il.issue_number,
                    "link_type": il.link_type,
                    "raw_reference": il.raw_reference,
                }
                for il in getattr(commit, "issue_links", [])
            ]

            c_dict = {
                "commit_hash": commit.commit_hash,
                "author_name": commit.author_name,
                "author_email": commit.author_email,
                "committed_at": commit.committed_at.isoformat(),
                "message": commit.message,
                "change_type": change.change_type.value,
                "insertions": change.insertions,
                "deletions": change.deletions,
                "linked_pull_requests": linked_prs,
                "linked_issues": linked_issues,
            }
            commits_data.append(c_dict)

            # Track author activity
            author_key = commit.author_email or commit.author_name
            if author_key not in authors_map:
                authors_map[author_key] = {
                    "name": commit.author_name,
                    "email": commit.author_email,
                    "commit_count": 0,
                }
            authors_map[author_key]["commit_count"] += 1

            if change.change_type == ChangeType.ADDED:
                introducing_commit = c_dict

        # If no explicit 'added' commit found, the oldest commit in the series is the introducing commit
        if not introducing_commit and commits_data:
            introducing_commit = commits_data[-1]

        authors_list = sorted(
            authors_map.values(), key=lambda a: a["commit_count"], reverse=True
        )

        return FileHistoryResult(
            file_path=file_path,
            total_commits=len(commits_data),
            introducing_commit=introducing_commit,
            commits=commits_data,
            authors=authors_list,
        )

    async def get_component_history(
        self,
        repository_id: uuid.UUID,
        component_path: str,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        """Retrieve aggregated commit history touching any file in component_path."""
        stmt = (
            select(Commit, CommitFileChange)
            .join(CommitFileChange, Commit.id == CommitFileChange.commit_id)
            .where(
                Commit.repository_id == repository_id,
                CommitFileChange.file_path.startswith(component_path),
            )
            .order_by(Commit.committed_at.desc())
        )
        rows = (await db.execute(stmt)).all()

        seen_commits = set()
        unique_commits: List[Dict[str, Any]] = []
        authors_map: Dict[str, int] = {}
        files_touched: Dict[str, int] = {}

        for commit, change in rows:
            if commit.id not in seen_commits:
                seen_commits.add(commit.id)
                linked_prs = [
                    {
                        "pr_number": pl.pr_number,
                        "link_type": pl.link_type,
                        "raw_reference": pl.raw_reference,
                    }
                    for pl in getattr(commit, "pull_request_links", [])
                ]
                linked_issues = [
                    {
                        "issue_number": il.issue_number,
                        "link_type": il.link_type,
                        "raw_reference": il.raw_reference,
                    }
                    for il in getattr(commit, "issue_links", [])
                ]
                unique_commits.append({
                    "commit_hash": commit.commit_hash,
                    "author_name": commit.author_name,
                    "author_email": commit.author_email,
                    "committed_at": commit.committed_at.isoformat(),
                    "message": commit.message,
                    "files_changed_count": commit.files_changed_count,
                    "insertions": commit.insertions,
                    "deletions": commit.deletions,
                    "linked_pull_requests": linked_prs,
                    "linked_issues": linked_issues,
                })
                authors_map[commit.author_name] = authors_map.get(commit.author_name, 0) + 1

            files_touched[change.file_path] = files_touched.get(change.file_path, 0) + 1

        introducing_commit = unique_commits[-1] if unique_commits else None

        return {
            "component_path": component_path,
            "total_commits": len(unique_commits),
            "introducing_commit": introducing_commit,
            "commits": unique_commits[:30],
            "top_authors": [{"name": k, "commits": v} for k, v in sorted(authors_map.items(), key=lambda x: x[1], reverse=True)],
            "files_touched": [{"path": k, "modifications": v} for k, v in sorted(files_touched.items(), key=lambda x: x[1], reverse=True)],
        }

    @staticmethod
    def parse_synthetic_payload(
        payload: List[Dict[str, Any]]
    ) -> List[ParsedCommit]:
        """Convert JSON commit payload to ParsedCommit list."""
        parsed: List[ParsedCommit] = []
        for item in payload:
            raw_time = item.get("committed_at")
            if isinstance(raw_time, str):
                try:
                    committed_at = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
                except ValueError:
                    committed_at = datetime.now(timezone.utc)
            elif isinstance(raw_time, datetime):
                committed_at = raw_time
            else:
                committed_at = datetime.now(timezone.utc)

            file_changes = []
            for fc in item.get("file_changes", []):
                ctype_str = str(fc.get("change_type", "modified")).lower()
                ctype = ChangeType(ctype_str) if ctype_str in [c.value for c in ChangeType] else ChangeType.MODIFIED
                file_changes.append(
                    ParsedFileChange(
                        file_path=fc.get("file_path", ""),
                        change_type=ctype,
                        insertions=int(fc.get("insertions", 0)),
                        deletions=int(fc.get("deletions", 0)),
                        old_path=fc.get("old_path"),
                    )
                )

            # If no explicit file_changes given but files list is given
            if not file_changes and item.get("files"):
                for f in item["files"]:
                    file_changes.append(
                        ParsedFileChange(
                            file_path=f,
                            change_type=ChangeType.MODIFIED,
                            insertions=10,
                            deletions=2,
                        )
                    )

            parsed.append(
                ParsedCommit(
                    commit_hash=item.get("commit_hash") or item.get("hash") or f"sha_{uuid.uuid4().hex[:8]}",
                    author_name=item.get("author_name") or item.get("author") or "Developer",
                    author_email=item.get("author_email") or "dev@example.com",
                    committed_at=committed_at,
                    message=item.get("message", "Commit update"),
                    parent_hashes=item.get("parent_hashes", []),
                    file_changes=file_changes,
                )
            )
        return parsed
