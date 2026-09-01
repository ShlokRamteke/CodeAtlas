from __future__ import annotations

from app.history.reference_extractor import ReferenceExtractor


def test_extract_pr_merge_commits():
    msg = "Merge pull request #45 from feature/auth\n\nAdd OAuth2 authentication"
    refs = ReferenceExtractor.extract_from_commit(msg)

    assert len(refs.pull_requests) == 1
    assert refs.pull_requests[0].pr_number == 45
    assert refs.pull_requests[0].link_type == "merges"
    assert refs.pull_requests[0].confidence == 1.0


def test_extract_squash_merge_commit():
    msg = "feat(cache): implement redis caching layer (#102)"
    refs = ReferenceExtractor.extract_from_commit(msg)

    assert len(refs.pull_requests) == 1
    assert refs.pull_requests[0].pr_number == 102
    assert refs.pull_requests[0].link_type == "merges"


def test_extract_explicit_pr_reference():
    msg = "fix memory leak in stream parser (PR #88)"
    refs = ReferenceExtractor.extract_from_commit(msg)

    assert any(pr.pr_number == 88 for pr in refs.pull_requests)


def test_extract_issue_closing_keywords():
    msg = "refactor: clean up db session management\n\nFixes #123, Closes #124, and resolves GH-125"
    refs = ReferenceExtractor.extract_from_commit(msg)

    issues = {i.issue_number: i.link_type for i in refs.issues}
    assert issues[123] == "fixes"
    assert issues[124] == "closes"
    assert issues[125] == "resolves"


def test_extract_issue_references():
    msg = "docs: update architecture diagram refs #55 and see #56"
    refs = ReferenceExtractor.extract_from_commit(msg)

    issues = {i.issue_number: i.link_type for i in refs.issues}
    assert 55 in issues
    assert 56 in issues


def test_extract_combined_pr_and_issue():
    msg = "Merge pull request #42 from bugfix/payment\n\nFixes #99 and closes issue #100"
    refs = ReferenceExtractor.extract_from_commit(msg)

    assert len(refs.pull_requests) == 1
    assert refs.pull_requests[0].pr_number == 42
    assert any(i.issue_number == 99 for i in refs.issues)
    assert any(i.issue_number == 100 for i in refs.issues)


def test_extract_from_pull_request_body():
    title = "feat: Add billing webhooks"
    body = "This PR connects Stripe webhooks to database.\n\nCloses #201\nRefs #202"
    issues = ReferenceExtractor.extract_from_pull_request(title, body)

    issue_map = {i.issue_number: i.link_type for i in issues}
    assert issue_map[201] == "closes"
    assert issue_map[202] == "references"
