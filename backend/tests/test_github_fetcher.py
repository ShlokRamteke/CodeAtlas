from __future__ import annotations

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
