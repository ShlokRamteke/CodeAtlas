from __future__ import annotations

import asyncio
import logging

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.history.git_indexer import ChangeType, ParsedCommit, ParsedFileChange
from app.ingestion.engine import IGNORED_DIRS, SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)

GITHUB_GRAPHQL_ENDPOINT = "https://api.github.com/graphql"

GRAPHQL_REPO_ARCHAEOLOGY_QUERY = """
query RepoArchaeology(
  $owner: String!
  $name: String!
  $numCommits: Int!
  $numPRs: Int!
  $numIssues: Int!
) {
  repository(owner: $owner, name: $name) {
    name
    description
    defaultBranchRef {
      name
      target {
        ... on Commit {
          history(first: $numCommits) {
            nodes {
              oid
              message
              committedDate
              additions
              deletions
              author {
                name
                email
                user {
                  login
                }
              }

              parents(first: 10) {
                nodes {
                  oid
                }
              }
              associatedPullRequests(first: 5) {
                nodes {
                  number
                  title
                  state
                }
              }
            }
          }
        }
      }
    }
    pullRequests(first: $numPRs, orderBy: {field: CREATED_AT, direction: DESC}) {
      nodes {
        number
        title
        body
        state
        merged
        mergedAt
        closedAt
        createdAt
        url
        author {
          login
        }
        labels(first: 10) {
          nodes {
            name
          }
        }
        closingIssuesReferences(first: 10) {
          nodes {
            number
            title
            state
          }
        }
      }
    }
    issues(first: $numIssues, orderBy: {field: CREATED_AT, direction: DESC}) {
      nodes {
        number
        title
        body
        state
        closedAt
        createdAt
        url
        author {
          login
        }
        labels(first: 10) {
          nodes {
            name
          }
        }
      }
    }
  }
}
"""


class GitHubRepoFetcher:
    """Fetcher for public and authenticated GitHub repositories supporting both GraphQL API v4 and REST API v3."""

    @staticmethod
    def parse_repo_url(url_or_slug: str) -> tuple[str, str]:
        """Extract (owner, repo) from URL or slug like 'owner/repo'."""
        cleaned = url_or_slug.strip().rstrip("/")
        # Matches https://github.com/owner/repo or github.com/owner/repo or owner/repo
        match = re.search(r"(?:github\.com/)?([^/]+)/([^/]+?)(?:\.git)?$", cleaned)
        if not match:
            raise ValueError(f"Invalid GitHub repository URL or slug: '{url_or_slug}'")
        return match.group(1), match.group(2)

    async def execute_graphql_query(
        self,
        query: str,
        variables: dict[str, Any],
        github_token: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Execute a GraphQL query against GitHub GraphQL API v4.
        Returns the data dictionary if successful, or None on failure/unauthorized.
        """
        token = github_token or os.getenv("GITHUB_TOKEN")
        if not token:
            logger.debug("No GITHUB_TOKEN provided; skipping GraphQL API.")
            return None

        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "Project-Archaeologist",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                res = await client.post(
                    GITHUB_GRAPHQL_ENDPOINT,
                    json={"query": query, "variables": variables},
                    headers=headers,
                )
                if res.status_code != 200:
                    logger.warning(
                        "GitHub GraphQL returned status %d: %s",
                        res.status_code,
                        res.text[:200],
                    )
                    return None

                body = res.json()
                if "errors" in body:
                    logger.warning("GitHub GraphQL errors: %s", body.get("errors"))
                    # If partial data is available, we may still return data
                    return body.get("data")
                return body.get("data")
        except Exception as exc:
            logger.warning("GitHub GraphQL request failed: %s", exc)
            return None

    async def fetch_repo_bundle_graphql(
        self,
        owner: str,
        repo: str,
        max_commits: int = 30,
        max_prs: int = 30,
        max_issues: int = 30,
        github_token: Optional[str] = None,
    ) -> Optional[Tuple[List[ParsedCommit], List[Any], List[Any]]]:
        """
        Fetch Commits, Pull Requests, and Issues in a single batched GitHub GraphQL v4 query.
        Returns (commits, pull_requests, issues) or None if GraphQL is unavailable.
        """
        from app.history.historical_linker import ParsedIssue, ParsedPullRequest

        data = await self.execute_graphql_query(
            GRAPHQL_REPO_ARCHAEOLOGY_QUERY,
            {
                "owner": owner,
                "name": repo,
                "numCommits": max_commits,
                "numPRs": max_prs,
                "numIssues": max_issues,
            },
            github_token=github_token,
        )

        if not data or not data.get("repository"):
            return None

        repo_data = data["repository"]

        # 1. Parse Commits
        parsed_commits: List[ParsedCommit] = []
        default_branch_ref = repo_data.get("defaultBranchRef") or {}
        target = default_branch_ref.get("target") or {}
        history = target.get("history") or {}
        commit_nodes = history.get("nodes") or []

        for node in commit_nodes:
            raw_date = node.get("committedDate")
            try:
                committed_at = (
                    datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                    if raw_date
                    else datetime.now(timezone.utc)
                )
            except Exception:
                committed_at = datetime.now(timezone.utc)

            author_obj = node.get("author") or {}
            author_user = author_obj.get("user") or {}
            author_name = (
                author_obj.get("name")
                or author_user.get("login")
                or "Unknown"
            )
            author_email = author_obj.get("email") or "unknown@domain.com"
            parent_hashes = [p["oid"] for p in node.get("parents", {}).get("nodes", []) if "oid" in p]
            additions = int(node.get("additions", 0) or 0)
            deletions = int(node.get("deletions", 0) or 0)

            parsed_commits.append(
                ParsedCommit(
                    commit_hash=node.get("oid", ""),
                    author_name=author_name,
                    author_email=author_email,
                    committed_at=committed_at,
                    message=node.get("message", ""),
                    parent_hashes=parent_hashes,
                    file_changes=[],
                    insertions=additions,
                    deletions=deletions,
                )
            )

        # Concurrently fetch commit file changes via GitHub REST
        rest_headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "Project-Archaeologist-Agent",
        }
        active_token = github_token or os.getenv("GITHUB_TOKEN")
        if active_token:
            rest_headers["Authorization"] = f"Bearer {active_token}"

        async def fetch_commit_file_changes(sha: str) -> List[ParsedFileChange]:
            if not sha:
                return []
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    detail_res = await client.get(
                        f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}",
                        headers=rest_headers,
                    )
                    if detail_res.status_code == 200:
                        detail_data = detail_res.json()
                        changes: List[ParsedFileChange] = []
                        for f in detail_data.get("files", []):
                            status_str = f.get("status", "modified")
                            ctype = (
                                ChangeType.ADDED if status_str == "added"
                                else ChangeType.DELETED if status_str == "removed"
                                else ChangeType.RENAMED if status_str == "renamed"
                                else ChangeType.MODIFIED
                            )
                            changes.append(
                                ParsedFileChange(
                                    file_path=f.get("filename", ""),
                                    change_type=ctype,
                                    insertions=int(f.get("additions", 0) or 0),
                                    deletions=int(f.get("deletions", 0) or 0),
                                    old_path=f.get("previous_filename"),
                                )
                            )
                        return changes
            except Exception:
                pass
            return []

        if parsed_commits:
            file_fetch_tasks = [fetch_commit_file_changes(c.commit_hash) for c in parsed_commits]
            commit_file_results = await asyncio.gather(*file_fetch_tasks, return_exceptions=True)
            for idx, f_res in enumerate(commit_file_results):
                if isinstance(f_res, list) and f_res:
                    parsed_commits[idx].file_changes = f_res
                    parsed_commits[idx].insertions = sum(fc.insertions for fc in f_res)
                    parsed_commits[idx].deletions = sum(fc.deletions for fc in f_res)

        # 2. Parse Pull Requests
        parsed_prs: List[ParsedPullRequest] = []

        pr_nodes = (repo_data.get("pullRequests") or {}).get("nodes") or []
        for node in pr_nodes:
            merged_at = None
            if node.get("mergedAt"):
                try:
                    merged_at = datetime.fromisoformat(node["mergedAt"].replace("Z", "+00:00"))
                except Exception:
                    merged_at = None

            closed_at = None
            if node.get("closedAt"):
                try:
                    closed_at = datetime.fromisoformat(node["closedAt"].replace("Z", "+00:00"))
                except Exception:
                    closed_at = None

            created_at = None
            if node.get("createdAt"):
                try:
                    created_at = datetime.fromisoformat(node["createdAt"].replace("Z", "+00:00"))
                except Exception:
                    created_at = None

            state_raw = node.get("state", "OPEN")
            is_merged = node.get("merged", False)
            state = "merged" if is_merged else state_raw.lower()

            author = (node.get("author") or {}).get("login", "Unknown")
            labels = [lbl["name"] for lbl in (node.get("labels") or {}).get("nodes", []) if "name" in lbl]

            parsed_prs.append(
                ParsedPullRequest(
                    number=node.get("number", 0),
                    title=node.get("title", ""),
                    body=node.get("body"),
                    state=state,
                    author=author,
                    merged_at=merged_at,
                    closed_at=closed_at,
                    labels=labels,
                    html_url=node.get("url"),
                    created_at=created_at,
                )
            )

        # 3. Parse Issues
        parsed_issues: List[ParsedIssue] = []
        issue_nodes = (repo_data.get("issues") or {}).get("nodes") or []
        for node in issue_nodes:
            closed_at = None
            if node.get("closedAt"):
                try:
                    closed_at = datetime.fromisoformat(node["closedAt"].replace("Z", "+00:00"))
                except Exception:
                    closed_at = None

            created_at = None
            if node.get("createdAt"):
                try:
                    created_at = datetime.fromisoformat(node["createdAt"].replace("Z", "+00:00"))
                except Exception:
                    created_at = None

            author = (node.get("author") or {}).get("login", "Unknown")
            labels = [lbl["name"] for lbl in (node.get("labels") or {}).get("nodes", []) if "name" in lbl]

            parsed_issues.append(
                ParsedIssue(
                    number=node.get("number", 0),
                    title=node.get("title", ""),
                    body=node.get("body"),
                    state=node.get("state", "OPEN").lower(),
                    author=author,
                    closed_at=closed_at,
                    labels=labels,
                    html_url=node.get("url"),
                    created_at=created_at,
                )
            )

        return parsed_commits, parsed_prs, parsed_issues

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
        Fetch recent commit history via GitHub GraphQL API v4 (with REST fallback).
        """
        # 1. Attempt GraphQL API first if token is available
        token = github_token or os.getenv("GITHUB_TOKEN")
        if token:
            bundle = await self.fetch_repo_bundle_graphql(
                owner=owner,
                repo=repo,
                max_commits=max_commits,
                github_token=token,
            )
            if bundle and bundle[0]:
                return bundle[0]

        # 2. Fallback to GitHub REST API
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Project-Archaeologist",
        }
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
                    committed_at = (
                        datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
                        if raw_date
                        else datetime.now(timezone.utc)
                    )
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
                                ChangeType.ADDED
                                if status_str == "added"
                                else ChangeType.DELETED
                                if status_str == "removed"
                                else ChangeType.RENAMED
                                if status_str == "renamed"
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

    async def fetch_public_repo_pull_requests(
        self,
        owner: str,
        repo: str,
        max_prs: int = 30,
        github_token: Optional[str] = None,
    ) -> List[Any]:
        """Fetch recent pull requests and metadata via GitHub GraphQL API v4 (with REST fallback)."""
        # 1. Attempt GraphQL API first if token is available
        token = github_token or os.getenv("GITHUB_TOKEN")
        if token:
            bundle = await self.fetch_repo_bundle_graphql(
                owner=owner,
                repo=repo,
                max_prs=max_prs,
                github_token=token,
            )
            if bundle and bundle[1]:
                return bundle[1]

        # 2. Fallback to GitHub REST API
        from app.history.historical_linker import ParsedPullRequest

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Project-Archaeologist",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        parsed_prs: List[ParsedPullRequest] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/pulls?state=all&per_page={max_prs}",
                headers=headers,
            )
            if res.status_code != 200:
                return []

            prs_list = res.json()
            for pr in prs_list:
                merged_at = None
                if pr.get("merged_at"):
                    try:
                        merged_at = datetime.fromisoformat(pr["merged_at"].replace("Z", "+00:00"))
                    except Exception:
                        merged_at = None

                closed_at = None
                if pr.get("closed_at"):
                    try:
                        closed_at = datetime.fromisoformat(pr["closed_at"].replace("Z", "+00:00"))
                    except Exception:
                        closed_at = None

                created_at = None
                if pr.get("created_at"):
                    try:
                        created_at = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
                    except Exception:
                        created_at = None

                labels = [
                    lbl["name"] if isinstance(lbl, dict) else str(lbl)
                    for lbl in pr.get("labels", [])
                ]

                parsed_prs.append(
                    ParsedPullRequest(
                        number=pr.get("number", 0),
                        title=pr.get("title", ""),
                        body=pr.get("body"),
                        state=pr.get("state", "open"),
                        author=pr.get("user", {}).get("login", "Unknown") if isinstance(pr.get("user"), dict) else "Unknown",
                        merged_at=merged_at,
                        closed_at=closed_at,
                        labels=labels,
                        html_url=pr.get("html_url"),
                        created_at=created_at,
                    )
                )

        return parsed_prs

    async def fetch_public_repo_issues(
        self,
        owner: str,
        repo: str,
        max_issues: int = 30,
        github_token: Optional[str] = None,
    ) -> List[Any]:
        """Fetch recent repository issues via GitHub GraphQL API v4 (with REST fallback)."""
        # 1. Attempt GraphQL API first if token is available
        token = github_token or os.getenv("GITHUB_TOKEN")
        if token:
            bundle = await self.fetch_repo_bundle_graphql(
                owner=owner,
                repo=repo,
                max_issues=max_issues,
                github_token=token,
            )
            if bundle and bundle[2]:
                return bundle[2]

        # 2. Fallback to GitHub REST API
        from app.history.historical_linker import ParsedIssue

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Project-Archaeologist",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        parsed_issues: List[ParsedIssue] = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/issues?state=all&per_page={max_issues}",
                headers=headers,
            )
            if res.status_code != 200:
                return []

            issues_list = res.json()
            for item in issues_list:
                # GitHub /issues returns pull requests as well; filter them out
                if "pull_request" in item:
                    continue

                closed_at = None
                if item.get("closed_at"):
                    try:
                        closed_at = datetime.fromisoformat(item["closed_at"].replace("Z", "+00:00"))
                    except Exception:
                        closed_at = None

                created_at = None
                if item.get("created_at"):
                    try:
                        created_at = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
                    except Exception:
                        created_at = None

                labels = [
                    lbl["name"] if isinstance(lbl, dict) else str(lbl)
                    for lbl in item.get("labels", [])
                ]

                parsed_issues.append(
                    ParsedIssue(
                        number=item.get("number", 0),
                        title=item.get("title", ""),
                        body=item.get("body"),
                        state=item.get("state", "open"),
                        author=item.get("user", {}).get("login", "Unknown") if isinstance(item.get("user"), dict) else "Unknown",
                        closed_at=closed_at,
                        labels=labels,
                        html_url=item.get("html_url"),
                        created_at=created_at,
                    )
                )

        return parsed_issues
