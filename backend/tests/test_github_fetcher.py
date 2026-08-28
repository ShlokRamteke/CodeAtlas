from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ingestion.github_fetcher import GitHubRepoFetcher


def test_parse_github_url_and_slug() -> None:
    fetcher = GitHubRepoFetcher()

    owner, repo = fetcher.parse_repo_url("https://github.com/ShlokRamteke/archlogist-prg")
    assert owner == "ShlokRamteke"
    assert repo == "archlogist-prg"

    owner, repo = fetcher.parse_repo_url("facebook/react.git")
    assert owner == "facebook"
    assert repo == "react"

    owner, repo = fetcher.parse_repo_url("fastapi/fastapi")
    assert owner == "fastapi"
    assert repo == "fastapi"

    with pytest.raises(ValueError):
        fetcher.parse_repo_url("invalid-url-with-no-slash")


@pytest.mark.asyncio
async def test_fetch_public_repo_pull_requests_mocked():
    fetcher = GitHubRepoFetcher()

    mock_pr_response = [
        {
            "number": 101,
            "title": "feat: async client improvements",
            "body": "Fixes #55",
            "state": "closed",
            "user": {"login": "octocat"},
            "merged_at": "2026-01-01T00:00:00Z",
            "labels": [{"name": "enhancement"}],
            "html_url": "https://github.com/octocat/repo/pull/101",
        }
    ]

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_pr_response
        mock_get.return_value = mock_resp

        prs = await fetcher.fetch_public_repo_pull_requests("octocat", "repo")
        assert len(prs) == 1
        assert prs[0].number == 101
        assert prs[0].title == "feat: async client improvements"
        assert prs[0].author == "octocat"
        assert prs[0].labels == ["enhancement"]


@pytest.mark.asyncio
async def test_fetch_public_repo_issues_mocked():
    fetcher = GitHubRepoFetcher()

    mock_issue_response = [
        {
            "number": 55,
            "title": "Async client connection timeout on high load",
            "body": "Need to tune connection pool.",
            "state": "closed",
            "user": {"login": "maintainer"},
            "closed_at": "2026-01-01T00:00:00Z",
            "labels": [{"name": "bug"}],
            "html_url": "https://github.com/octocat/repo/issues/55",
        },
        {
            "number": 101,
            "title": "A pull request returned by /issues",
            "pull_request": {"url": "..."},  # Should be filtered out
        },
    ]

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_issue_response
        mock_get.return_value = mock_resp

        issues = await fetcher.fetch_public_repo_issues("octocat", "repo")
        assert len(issues) == 1
        assert issues[0].number == 55
        assert issues[0].title == "Async client connection timeout on high load"
        assert issues[0].labels == ["bug"]


@pytest.mark.asyncio
async def test_fetch_repo_bundle_graphql_mocked():
    fetcher = GitHubRepoFetcher()

    mock_graphql_data = {
        "repository": {
            "name": "archlogist-prg",
            "description": "Archaeologist engine",
            "defaultBranchRef": {
                "name": "main",
                "target": {
                    "history": {
                        "nodes": [
                            {
                                "oid": "c1a2b3c4d5e6",
                                "message": "feat(core): initial tree-sitter AST parser (#12)",
                                "committedDate": "2026-01-10T12:00:00Z",
                                "author": {
                                    "name": "Alex Architect",
                                    "email": "alex@archaeologist.dev",
                                    "user": {"login": "alexarch"},
                                },
                                "parents": {"nodes": [{"oid": "root000"}]},
                                "associatedPullRequests": {
                                    "nodes": [
                                        {"number": 12, "title": "Tree-sitter parser", "state": "MERGED"}
                                    ]
                                },
                            }
                        ]
                    }
                },
            },
            "pullRequests": {
                "nodes": [
                    {
                        "number": 12,
                        "title": "feat(core): initial tree-sitter AST parser",
                        "body": "Implements AST symbol extraction.\n\nCloses #5",
                        "state": "MERGED",
                        "merged": True,
                        "mergedAt": "2026-01-10T12:00:00Z",
                        "closedAt": "2026-01-10T12:00:00Z",
                        "createdAt": "2026-01-09T10:00:00Z",
                        "url": "https://github.com/org/repo/pull/12",
                        "author": {"login": "alexarch"},
                        "labels": {"nodes": [{"name": "ast"}, {"name": "core"}]},
                        "closingIssuesReferences": {
                            "nodes": [
                                {"number": 5, "title": "Parse multi-language ASTs", "state": "CLOSED"}
                            ]
                        },
                    }
                ]
            },
            "issues": {
                "nodes": [
                    {
                        "number": 5,
                        "title": "Parse multi-language ASTs",
                        "body": "Need Tree-sitter integration for Python and TypeScript.",
                        "state": "CLOSED",
                        "closedAt": "2026-01-10T12:00:00Z",
                        "createdAt": "2026-01-08T09:00:00Z",
                        "url": "https://github.com/org/repo/issues/5",
                        "author": {"login": "lead-dev"},
                        "labels": {"nodes": [{"name": "enhancement"}]},
                    }
                ]
            },
        }
    }

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"data": mock_graphql_data}
        mock_post.return_value = mock_resp

        bundle = await fetcher.fetch_repo_bundle_graphql(
            "org", "repo", max_commits=10, max_prs=10, max_issues=10, github_token="ghp_fake_token"
        )

        assert bundle is not None
        commits, prs, issues = bundle

        # Verify Commits
        assert len(commits) == 1
        assert commits[0].commit_hash == "c1a2b3c4d5e6"
        assert commits[0].author_name == "Alex Architect"
        assert commits[0].author_email == "alex@archaeologist.dev"
        assert commits[0].parent_hashes == ["root000"]
        assert "initial tree-sitter AST parser" in commits[0].message

        # Verify PRs
        assert len(prs) == 1
        assert prs[0].number == 12
        assert prs[0].state == "merged"
        assert prs[0].author == "alexarch"
        assert prs[0].labels == ["ast", "core"]

        # Verify Issues
        assert len(issues) == 1
        assert issues[0].number == 5
        assert issues[0].state == "closed"
        assert issues[0].author == "lead-dev"
        assert issues[0].labels == ["enhancement"]


@pytest.mark.asyncio
async def test_graphql_fallback_when_unauthorized():
    fetcher = GitHubRepoFetcher()

    # When GraphQL fails with 401 Unauthorized, it returns None
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Bad credentials"
        mock_post.return_value = mock_resp

        data = await fetcher.execute_graphql_query(
            "query { viewer { login } }", {}, github_token="invalid_token"
        )
        assert data is None
