from __future__ import annotations

from app.parser.doc_parser import (
    DocType,
    EngineeringContextParser,
    ParsedADRStatus,
    ParsedConstraintCategory,
    ParsedConstraintLevel,
)


def test_classify_doc_type():
    assert EngineeringContextParser.classify_doc_type("README.md") == DocType.README
    assert EngineeringContextParser.classify_doc_type("docs/README.txt") == DocType.README
    assert EngineeringContextParser.classify_doc_type("ARCHITECTURE.md") == DocType.ARCHITECTURE
    assert (
        EngineeringContextParser.classify_doc_type("docs/architecture/system.md")
        == DocType.ARCHITECTURE
    )
    assert (
        EngineeringContextParser.classify_doc_type("docs/adr/0001-use-postgres.md") == DocType.ADR
    )
    assert EngineeringContextParser.classify_doc_type("decisions/0002-jwt-auth.md") == DocType.ADR
    assert EngineeringContextParser.classify_doc_type("DECISIONS.md") == DocType.ADR
    assert EngineeringContextParser.classify_doc_type("TESTING.md") == DocType.TESTING_GUIDE
    assert EngineeringContextParser.classify_doc_type("docs/testing.md") == DocType.TESTING_GUIDE
    assert EngineeringContextParser.classify_doc_type("docs/design/specs.md") == DocType.DESIGN_DOC
    assert EngineeringContextParser.classify_doc_type("CONTRIBUTING.md") == DocType.GENERAL_DOC


def test_extract_adr_status_and_deciders():
    content = """# 1. Use PostgreSQL with pgvector

## Status
Accepted

## Deciders
Core Architecture Team, Jane Doe

## Context
We need a durable, transactional relational store.
"""
    status, deciders = EngineeringContextParser.extract_adr_status(content)
    assert status == ParsedADRStatus.ACCEPTED
    assert deciders == "Core Architecture Team, Jane Doe"

    superseded_content = """# 2. SQLite In-Memory
Status: Superseded
"""
    status2, deciders2 = EngineeringContextParser.extract_adr_status(superseded_content)
    assert status2 == ParsedADRStatus.SUPERSEDED
    assert deciders2 is None


def test_extract_sections():
    content = """# Project Title
Introductory text.

## Architecture
Architecture overview text.

### Storage
Postgres details.
"""
    sections = EngineeringContextParser.extract_sections(content)
    assert len(sections) == 3
    assert sections[0].heading == "Project Title"
    assert sections[0].level == 1
    assert sections[1].heading == "Architecture"
    assert sections[1].level == 2
    assert sections[2].heading == "Storage"
    assert sections[2].level == 3


def test_extract_constraints_rfc2119():
    content = """# Engineering Guidelines

- The system MUST sanitize all user inputs before SQL execution.
- Never store raw passwords or unencrypted api tokens in logs.
- Developers SHOULD keep functions under 50 lines.
- Database migrations MUST NOT cause data loss or breaking downtime.
- Invariant: all endpoints require valid authorization tokens.
"""
    constraints = EngineeringContextParser.extract_constraints("docs/guidelines.md", content)
    assert len(constraints) == 5

    # Check security constraint
    c_sql = next(c for c in constraints if "sanitize all user inputs" in c.statement)
    assert c_sql.level == ParsedConstraintLevel.MUST
    assert c_sql.category == ParsedConstraintCategory.SECURITY

    # Check password/secret constraint
    c_pwd = next(c for c in constraints if "Never store raw passwords" in c.statement)
    assert c_pwd.level == ParsedConstraintLevel.MUST_NOT
    assert c_pwd.category == ParsedConstraintCategory.SECURITY

    # Check recommendation
    c_should = next(c for c in constraints if "under 50 lines" in c.statement)
    assert c_should.level == ParsedConstraintLevel.SHOULD

    # Check data integrity constraint
    c_data = next(c for c in constraints if "data loss" in c.statement)
    assert c_data.level == ParsedConstraintLevel.MUST_NOT
    assert c_data.category == ParsedConstraintCategory.DATA_INTEGRITY

    # Check invariant
    c_inv = next(c for c in constraints if "all endpoints require" in c.statement)
    assert c_inv.level == ParsedConstraintLevel.MUST
    assert c_inv.confidence == 1.0


def test_parse_doc_full():
    content = """# Architecture Decisions

This document describes the architectural decisions for Project Archaeologist.

## Security Rules
- Secret-scan MUST occur before persistence.
- Arbitrary code execution is strictly prohibited; NEVER run untrusted code.
"""
    parsed = EngineeringContextParser.parse_doc(
        "docs/decisions/0001-arch.md", content, "fakehash123"
    )
    assert parsed.title == "Architecture Decisions"
    assert parsed.doc_type == DocType.ADR
    assert len(parsed.sections) == 2
    assert len(parsed.constraints) == 2
    assert any(c.level == ParsedConstraintLevel.MUST_NOT for c in parsed.constraints)
