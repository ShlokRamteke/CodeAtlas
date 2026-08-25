from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import httpx

from app.history.git_indexer import ChangeType, ParsedCommit, ParsedFileChange
from app.ingestion.engine import IGNORED_DIRS, SUPPORTED_EXTENSIONS


class GitHubRepoFetcher:
    """Read-only fetcher for public GitHub repositories."""

    @staticmethod
    def parse_repo_url(url_or_slug: str) -> tuple[str, str]:
        """Extract (owner, repo) from URL or slug like 'owner/repo'."""
        cleaned = url_or_slug.strip().rstrip("/")
        # Matches https://github.com/owner/repo or github.com/owner/repo or owner/repo
        match = re.search(r"(?:github\.com/)?([^/]+)/([^/]+?)(?:\.git)?$", cleaned)
        if not match:
            raise ValueError(f"Invalid GitHub repository URL or slug: '{url_or_slug}'")
        return match.group(1), match.group(2)

    async def fetch_public_repo_files(
        self,
        owner: str,
        repo: str,
        max_files: int = 200,
        github_token: Optional[str] = None,
    ) -> tuple[Dict[str, str], str]:
        """
        Fetch repository source files via GitHub REST API.
        Returns ({relative_path: content}, default_branch).
        """
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Project-Archaeologist",
        }
        token = github_token or os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Get repo metadata to get default branch
            repo_res = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}", headers=headers
            )
            if repo_res.status_code == 404:
                raise ValueError(f"GitHub repository '{owner}/{repo}' not found or is private.")
            if repo_res.status_code != 200:
                raise ValueError(
                    f"GitHub API returned error {repo_res.status_code}: {repo_res.text}"
                )

            repo_meta = repo_res.json()
            default_branch = repo_meta.get("default_branch", "main")

            # 2. Fetch Git Tree recursively
            tree_res = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1",
                headers=headers,
            )
            if tree_res.status_code != 200:
                raise ValueError(
                    f"Failed to fetch repository tree: {tree_res.status_code} {tree_res.text}"
                )

            tree_data = tree_res.json()
            tree_items = tree_data.get("tree", [])

            # 3. Filter supported source code files
            candidate_files = []
            for item in tree_items:
                if item.get("type") == "blob":
                    path = item.get("path", "")
                    ext = Path(path).suffix.lower()
                    parts = Path(path).parts

                    # Check ignored directories
                    if any(p in IGNORED_DIRS or p.startswith(".") for p in parts[:-1]):
                        continue

                    if ext in SUPPORTED_EXTENSIONS:
                        candidate_files.append(path)
                        if len(candidate_files) >= max_files:
                            break

            # 4. Fetch raw content for candidate files via raw.githubusercontent.com
            files_content: Dict[str, str] = {}
            for path in candidate_files:
                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{default_branch}/{path}"
                try:
                    res = await client.get(raw_url, headers=headers)
                    if res.status_code == 200:
                        files_content[path] = res.text
                except Exception:
                    continue

            return files_content, default_branch

    async def fetch_public_repo_commits(
        self,
        owner: str,
        repo: str,
        max_commits: int = 30,
        github_token: Optional[str] = None,
    ) -> List[ParsedCommit]:
        """
        Fetch recent commit history and changed files via GitHub REST API.
        """
        from app.history.git_indexer import ParsedCommit, ParsedFileChange

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Project-Archaeologist",
        }
        token = github_token or os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"

        parsed_commits: List[ParsedCommit] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/commits?per_page={max_commits}",
                headers=headers,
            )
            if res.status_code != 200:
                return []

            commits_list = res.json()
            for c in commits_list:
                sha = c.get("sha", "")
                commit_info = c.get("commit", {})
                author_info = commit_info.get("author", {})
                author_name = author_info.get("name", "Unknown")
                author_email = author_info.get("email", "unknown@domain.com")
                raw_date = author_info.get("date")
                message = commit_info.get("message", "")

                try:
                    committed_at = datetime.fromisoformat(raw_date.replace("Z", "+00:00")) if raw_date else datetime.now(timezone.utc)
                except Exception:
                    committed_at = datetime.now(timezone.utc)

                parent_hashes = [p.get("sha", "") for p in c.get("parents", [])]

                # Fetch individual commit details to obtain changed files if needed
                file_changes: List[ParsedFileChange] = []
                try:
                    detail_res = await client.get(
                        f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}",
                        headers=headers,
                    )
                    if detail_res.status_code == 200:
                        detail_data = detail_res.json()
                        for f in detail_data.get("files", []):
                            status_str = f.get("status", "modified")
                            ctype = (
                                ChangeType.ADDED if status_str == "added"
                                else ChangeType.DELETED if status_str == "removed"
                                else ChangeType.RENAMED if status_str == "renamed"
                                else ChangeType.MODIFIED
                            )
                            file_changes.append(
                                ParsedFileChange(
                                    file_path=f.get("filename", ""),
                                    change_type=ctype,
                                    insertions=f.get("additions", 0),
                                    deletions=f.get("deletions", 0),
                                    old_path=f.get("previous_filename"),
                                )
                            )
                except Exception:
                    pass

                parsed_commits.append(
                    ParsedCommit(
                        commit_hash=sha,
                        author_name=author_name,
                        author_email=author_email,
                        committed_at=committed_at,
                        message=message,
                        parent_hashes=parent_hashes,
                        file_changes=file_changes,
                    )
                )

        return parsed_commits

