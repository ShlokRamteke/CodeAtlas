from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


class DocType(str, enum.Enum):
    README = "readme"
    ARCHITECTURE = "architecture"
    ADR = "adr"
    DESIGN_DOC = "design_doc"
    TESTING_GUIDE = "testing_guide"
    GENERAL_DOC = "general_doc"


class ParsedADRStatus(str, enum.Enum):
    ACCEPTED = "accepted"
    SUPERSEDED = "superseded"
    PROPOSED = "proposed"
    DEPRECATED = "deprecated"
    DRAFT = "draft"
    NA = "n/a"


class ParsedConstraintCategory(str, enum.Enum):
    SECURITY = "security"
    PERFORMANCE = "performance"
    ARCHITECTURE = "architecture"
    TESTING = "testing"
    DATA_INTEGRITY = "data_integrity"
    GENERAL = "general"


class ParsedConstraintLevel(str, enum.Enum):
    MUST = "must"
    SHOULD = "should"
    MUST_NOT = "must_not"


@dataclass
class ParsedConstraint:
    category: ParsedConstraintCategory
    level: ParsedConstraintLevel
    title: str
    statement: str
    source_path: str
    line_start: int
    line_end: int
    confidence: float = 1.0
    extra_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedSection:
    heading: str
    level: int
    content: str
    line_start: int
    line_end: int


@dataclass
class ParsedEngineeringDoc:
    path: str
    doc_type: DocType
    title: str
    format: str
    content_hash: str
    status: ParsedADRStatus
    deciders: Optional[str]
    raw_content: str
    summary: Optional[str]
    sections: List[ParsedSection] = field(default_factory=list)
    constraints: List[ParsedConstraint] = field(default_factory=list)
    extra_metadata: Dict[str, Any] = field(default_factory=dict)


# RFC 2119 / Invariant regex trigger patterns
MUST_NOT_PATTERNS = [
    re.compile(r"\b(?:must not|shall not|never|do not|cannot)\b", re.IGNORECASE),
]

MUST_PATTERNS = [
    re.compile(
        r"\b(?:must|shall|required|always|invariant|strictly required)\b",
        re.IGNORECASE,
    ),
]

SHOULD_PATTERNS = [
    re.compile(r"\b(?:should|recommended|strongly encouraged|ought to)\b", re.IGNORECASE),
]

# Topic categorization regexes
CATEGORY_PATTERNS = {
    ParsedConstraintCategory.SECURITY: re.compile(
        r"\b(?:secur\w*|secrets?|credentials?|tokens?|passwords?|auth\w*|sandbox\w*|sanitiz\w*|cve\w*|vulnerabilit\w*|privilege\w*|tenant isolation)\b",
        re.IGNORECASE,
    ),
    ParsedConstraintCategory.PERFORMANCE: re.compile(
        r"\b(?:performan\w*|latency|throughput|memor\w*|cach\w*|concurren\w*|timeout\w*|scal\w*|async\w*|o\(n\)|bottleneck\w*|slow)\b",
        re.IGNORECASE,
    ),
    ParsedConstraintCategory.TESTING: re.compile(
        r"\b(?:test\w*|coverage|fixtures?|mocks?|assert\w*|evaluat\w*|benchmark\w*|regression\w*)\b",
        re.IGNORECASE,
    ),
    ParsedConstraintCategory.DATA_INTEGRITY: re.compile(
        r"\b(?:data loss|integrity|transaction\w*|acid|rollback\w*|schema\w*|migrat\w*|idempotent\w*|consisten\w*|persist\w*)\b",
        re.IGNORECASE,
    ),
    ParsedConstraintCategory.ARCHITECTURE: re.compile(
        r"\b(?:architect\w*|dependenc\w*|boundar\w*|layer\w*|interfac\w*|module\w*|abstract\w*|coupl\w*|contract\w*|design\w*|isolat\w*)\b",
        re.IGNORECASE,
    ),
}


class EngineeringContextParser:
    """
    Deterministic parser for Markdown, ADRs, architecture docs, and design constraints.
    Operates strictly without LLM calls.
    """

    @classmethod
    def classify_doc_type(cls, path: str) -> DocType:
        norm = path.lower().replace("\\", "/")
        fname = norm.split("/")[-1]

        # README
        if fname.startswith("readme"):
            return DocType.README

        # Architecture Docs
        if "architecture" in norm or fname in ("arch.md", "architecture.md"):
            return DocType.ARCHITECTURE

        # ADRs (Architecture Decision Records)
        if (
            "/adr/" in norm
            or norm.startswith("adr/")
            or "/decisions/" in norm
            or norm.startswith("decisions/")
            or fname == "decisions.md"
            or re.match(r"^\d{4}-.*\.md$", fname)
        ):
            return DocType.ADR

        # Testing Guide
        if (
            fname in ("testing.md", "tests.md")
            or norm.endswith("/testing.md")
            or "/test/" in norm
            or "test_plan" in fname
        ):
            return DocType.TESTING_GUIDE

        # Design Docs / RFCs
        if "design" in norm or fname.startswith("rfc") or fname in ("design.md", "spec.md"):
            return DocType.DESIGN_DOC

        return DocType.GENERAL_DOC

    @classmethod
    def extract_adr_status(cls, content: str) -> Tuple[ParsedADRStatus, Optional[str]]:
        """Extract ADR status (e.g. accepted, superseded, proposed) and deciders."""
        status = ParsedADRStatus.NA
        deciders: Optional[str] = None

        # Check status patterns
        status_match = re.search(r"(?i)(?:##\s*Status|\bStatus\b)\s*[:\-\n]\s*([a-zA-Z]+)", content)
        if status_match:
            val = status_match.group(1).lower().strip()
            if val in ("accepted", "approved"):
                status = ParsedADRStatus.ACCEPTED
            elif val in ("superseded", "replaced"):
                status = ParsedADRStatus.SUPERSEDED
            elif val in ("proposed", "pending"):
                status = ParsedADRStatus.PROPOSED
            elif val in ("deprecated", "rejected"):
                status = ParsedADRStatus.DEPRECATED
            elif val in ("draft", "wip"):
                status = ParsedADRStatus.DRAFT

        # Check deciders pattern
        deciders_match = re.search(
            r"(?i)(?:deciders|decision makers|authors?)\s*[:\-\n]\s*([^\n\r]+)", content
        )
        if deciders_match:
            deciders = deciders_match.group(1).strip()

        return status, deciders

    @classmethod
    def extract_sections(cls, content: str) -> List[ParsedSection]:
        """Extract markdown sections with heading hierarchy and line spans."""
        lines = content.splitlines()
        sections: List[ParsedSection] = []

        current_heading = "Preamble"
        current_level = 0
        section_start = 1
        current_lines: List[str] = []

        for idx, line in enumerate(lines, start=1):
            heading_match = re.match(r"^(#{1,6})\s+(.*)$", line)
            if heading_match:
                if current_lines:
                    sections.append(
                        ParsedSection(
                            heading=current_heading,
                            level=current_level,
                            content="\n".join(current_lines).strip(),
                            line_start=section_start,
                            line_end=idx - 1,
                        )
                    )
                current_heading = heading_match.group(2).strip()
                current_level = len(heading_match.group(1))
                section_start = idx
                current_lines = [line]
            else:
                current_lines.append(line)

        if current_lines:
            sections.append(
                ParsedSection(
                    heading=current_heading,
                    level=current_level,
                    content="\n".join(current_lines).strip(),
                    line_start=section_start,
                    line_end=len(lines),
                )
            )

        return sections

    @classmethod
    def extract_constraints(cls, path: str, content: str) -> List[ParsedConstraint]:
        """
        Deterministically extract architectural invariants and design constraints
        using RFC 2119 rules and bulleted/numbered imperative directives.
        """
        lines = content.splitlines()
        constraints: List[ParsedConstraint] = []

        for idx, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line:
                continue

            # Strip list markdown markers
            is_list_item = False
            clean_line = line
            list_match = re.match(r"^(?:[-*+]|\d+\.)\s+(.*)$", line)
            if list_match:
                is_list_item = True
                clean_line = list_match.group(1).strip()

            # Skip trivial or heading lines unless they explicitly say "Constraint:" or "Invariant:"
            if clean_line.startswith("#"):
                continue

            # Determine constraint level
            level: Optional[ParsedConstraintLevel] = None
            if any(p.search(clean_line) for p in MUST_NOT_PATTERNS):
                level = ParsedConstraintLevel.MUST_NOT
            elif any(p.search(clean_line) for p in MUST_PATTERNS):
                level = ParsedConstraintLevel.MUST
            elif is_list_item and any(p.search(clean_line) for p in SHOULD_PATTERNS):
                level = ParsedConstraintLevel.SHOULD

            # Only treat as constraint if it matches an imperative trigger or explicit prefix
            has_explicit_prefix = bool(
                re.match(
                    r"^(?:constraint|invariant|rule|rule\s*\d+|requirement)\s*[:\-]",
                    clean_line,
                    re.I,
                )
            )
            if not level and not has_explicit_prefix:
                continue

            if not level and has_explicit_prefix:
                level = ParsedConstraintLevel.MUST

            # Categorize
            category = ParsedConstraintCategory.GENERAL
            for cat, pattern in CATEGORY_PATTERNS.items():
                if pattern.search(clean_line):
                    category = cat
                    break

            # Short concise title
            # Take up to 10 words or until first colon/period
            title_part = re.split(r"[:.]", clean_line)[0].strip()
            if len(title_part.split()) > 10:
                title_part = " ".join(title_part.split()[:8]) + "..."
            title = title_part if len(title_part) >= 5 else clean_line[:80]

            constraints.append(
                ParsedConstraint(
                    category=category,
                    level=level,  # type: ignore
                    title=title,
                    statement=clean_line,
                    source_path=path,
                    line_start=idx,
                    line_end=idx,
                    confidence=1.0 if has_explicit_prefix else 0.9,
                )
            )

        return constraints

    @classmethod
    def parse_doc(cls, path: str, content: str, content_hash: str) -> ParsedEngineeringDoc:
        """Parse engineering document into structured sections, metadata, and constraints."""
        doc_type = cls.classify_doc_type(path)
        sections = cls.extract_sections(content)
        constraints = cls.extract_constraints(path, content)

        # Determine title
        title = ""
        for s in sections:
            if s.level == 1:
                title = s.heading
                break
        if not title:
            first_line = content.strip().splitlines()[0] if content.strip() else ""
            if first_line.startswith("#"):
                title = first_line.lstrip("#").strip()
            else:
                title = path.split("/")[-1]

        # Extract summary: first non-heading paragraph
        summary = ""
        for line in content.splitlines():
            line_s = line.strip()
            if line_s and not line_s.startswith("#") and not line_s.startswith("```"):
                summary = line_s[:300]
                break

        status = ParsedADRStatus.NA
        deciders = None
        if doc_type == DocType.ADR:
            status, deciders = cls.extract_adr_status(content)

        return ParsedEngineeringDoc(
            path=path,
            doc_type=doc_type,
            title=title,
            format="markdown",
            content_hash=content_hash,
            status=status,
            deciders=deciders,
            raw_content=content,
            summary=summary or None,
            sections=sections,
            constraints=constraints,
            extra_metadata={
                "section_count": len(sections),
                "constraint_count": len(constraints),
            },
        )
