from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Set


@dataclass
class ExtractedPRRef:
    pr_number: int
    link_type: str  # 'merges' | 'references' | 'squash_merge'
    raw_match: str
    confidence: float = 1.0


@dataclass
class ExtractedIssueRef:
    issue_number: int
    link_type: str  # 'fixes' | 'closes' | 'resolves' | 'references' | 'mentions'
    raw_match: str
    confidence: float = 1.0


@dataclass
class ExtractedReferences:
    pull_requests: List[ExtractedPRRef] = field(default_factory=list)
    issues: List[ExtractedIssueRef] = field(default_factory=list)


class ReferenceExtractor:
    """
    Deterministic pattern extractor for PR and Issue cross-references
    in commit messages, PR descriptions, and issue bodies.
    """

    # 1. PR Reference Patterns
    # GitHub default merge commit: "Merge pull request #123 from ..."
    PR_MERGE_PATTERN = re.compile(
        r"(?:merge\s+pull\s+request\s+#|merge\s+pr\s+#|merged\s+pr\s+#)(\d+)",
        re.IGNORECASE,
    )
    # Squash merge suffix: "feat: something (#123)"
    PR_SQUASH_PATTERN = re.compile(
        r"\(\s*#(\d+)\s*\)(?:\s*$|\s+)",
        re.MULTILINE,
    )
    # Explicit PR mention: "PR #123", "PR: #123", "pull request #123"
    PR_EXPLICIT_PATTERN = re.compile(
        r"\b(?:pr|pull\s*request)\s*[:#]\s*#?(\d+)\b",
        re.IGNORECASE,
    )

    # 2. Issue Closing Patterns (GitHub closing keywords)
    # "fixes #123", "closes GH-45", "resolved #99"
    ISSUE_CLOSE_PATTERN = re.compile(
        r"\b(close|closes|closed|fix|fixes|fixed|resolve|resolves|resolved)\s+(?:gh-|#)?#?(\d+)\b",
        re.IGNORECASE,
    )

    # 3. Issue Reference Patterns
    # "refs #123", "references #45", "issue #67", "see #89", "GH-102"
    ISSUE_REF_PATTERN = re.compile(
        r"\b(ref|refs|references|see|issue|gh-)\s*[:#]?\s*#?(\d+)\b",
        re.IGNORECASE,
    )

    # 4. Generic #123 mention
    GENERIC_NUMBER_PATTERN = re.compile(
        r"(?<!\w)#(\d+)\b",
    )

    @classmethod
    def extract_from_commit(cls, message: str) -> ExtractedReferences:
        """Extract both PR and issue references from a Git commit message."""
        if not message:
            return ExtractedReferences()

        prs: List[ExtractedPRRef] = []
        issues: List[ExtractedIssueRef] = []
        seen_prs: Set[int] = set()
        seen_issues: Set[int] = set()

        # Check PR merge pattern
        for match in cls.PR_MERGE_PATTERN.finditer(message):
            pr_num = int(match.group(1))
            if pr_num not in seen_prs:
                seen_prs.add(pr_num)
                prs.append(
                    ExtractedPRRef(
                        pr_number=pr_num,
                        link_type="merges",
                        raw_match=match.group(0),
                        confidence=1.0,
                    )
                )

        # Check Squash merge pattern
        for match in cls.PR_SQUASH_PATTERN.finditer(message):
            pr_num = int(match.group(1))
            if pr_num not in seen_prs:
                seen_prs.add(pr_num)
                prs.append(
                    ExtractedPRRef(
                        pr_number=pr_num,
                        link_type="merges",
                        raw_match=match.group(0).strip(),
                        confidence=0.95,
                    )
                )

        # Check Explicit PR mentions
        for match in cls.PR_EXPLICIT_PATTERN.finditer(message):
            pr_num = int(match.group(1))
            if pr_num not in seen_prs:
                seen_prs.add(pr_num)
                prs.append(
                    ExtractedPRRef(
                        pr_number=pr_num,
                        link_type="references",
                        raw_match=match.group(0),
                        confidence=0.95,
                    )
                )

        # Check Issue closing keywords
        for match in cls.ISSUE_CLOSE_PATTERN.finditer(message):
            action = match.group(1).lower()
            issue_num = int(match.group(2))
            if issue_num not in seen_issues and issue_num not in seen_prs:
                seen_issues.add(issue_num)
                link_type = (
                    "fixes" if "fix" in action else "closes" if "close" in action else "resolves"
                )
                issues.append(
                    ExtractedIssueRef(
                        issue_number=issue_num,
                        link_type=link_type,
                        raw_match=match.group(0),
                        confidence=1.0,
                    )
                )

        # Check Issue reference keywords
        for match in cls.ISSUE_REF_PATTERN.finditer(message):
            issue_num = int(match.group(2))
            if issue_num not in seen_issues and issue_num not in seen_prs:
                seen_issues.add(issue_num)
                issues.append(
                    ExtractedIssueRef(
                        issue_number=issue_num,
                        link_type="references",
                        raw_match=match.group(0),
                        confidence=0.9,
                    )
                )

        # Check remaining generic #123 mentions
        for match in cls.GENERIC_NUMBER_PATTERN.finditer(message):
            num = int(match.group(1))
            if num not in seen_prs and num not in seen_issues:
                seen_issues.add(num)
                issues.append(
                    ExtractedIssueRef(
                        issue_number=num,
                        link_type="mentions",
                        raw_match=match.group(0),
                        confidence=0.75,
                    )
                )

        return ExtractedReferences(pull_requests=prs, issues=issues)

    @classmethod
    def extract_from_pull_request(
        cls, title: str, body: Optional[str] = None
    ) -> List[ExtractedIssueRef]:
        """Extract issue references from PR title and body description."""
        combined_text = f"{title or ''}\n{body or ''}"
        if not combined_text.strip():
            return []

        issues: List[ExtractedIssueRef] = []
        seen_issues: Set[int] = set()

        # Check closing keywords first
        for match in cls.ISSUE_CLOSE_PATTERN.finditer(combined_text):
            action = match.group(1).lower()
            issue_num = int(match.group(2))
            if issue_num not in seen_issues:
                seen_issues.add(issue_num)
                link_type = (
                    "fixes" if "fix" in action else "closes" if "close" in action else "resolves"
                )
                issues.append(
                    ExtractedIssueRef(
                        issue_number=issue_num,
                        link_type=link_type,
                        raw_match=match.group(0),
                        confidence=1.0,
                    )
                )

        # Check issue reference keywords
        for match in cls.ISSUE_REF_PATTERN.finditer(combined_text):
            issue_num = int(match.group(2))
            if issue_num not in seen_issues:
                seen_issues.add(issue_num)
                issues.append(
                    ExtractedIssueRef(
                        issue_number=issue_num,
                        link_type="references",
                        raw_match=match.group(0),
                        confidence=0.9,
                    )
                )

        # Check remaining generic #123
        for match in cls.GENERIC_NUMBER_PATTERN.finditer(combined_text):
            num = int(match.group(1))
            if num not in seen_issues:
                seen_issues.add(num)
                issues.append(
                    ExtractedIssueRef(
                        issue_number=num,
                        link_type="mentions",
                        raw_match=match.group(0),
                        confidence=0.75,
                    )
                )

        return issues
