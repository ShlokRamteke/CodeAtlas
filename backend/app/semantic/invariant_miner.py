"""Semantic Invariant & Architectural Constraint Miner.

Mines natural-language engineering rules and invariants from repository documentation
(README.md, ARCHITECTURE.md, ADRs, design docs) using fast, typed System One
decision models (/v1/systemone) with calibrated fallback heuristics.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.parser.doc_parser import (
    CATEGORY_PATTERNS,
    MUST_NOT_PATTERNS,
    MUST_PATTERNS,
    SHOULD_PATTERNS,
    EngineeringContextParser,
    ParsedConstraint,
    ParsedConstraintCategory,
    ParsedConstraintLevel,
)
from app.semantic.client import SystemOneClient
from app.semantic.systemone import (
    ChoiceQuestion,
    NoulQuestion,
    SystemOneQuestion,
)

logger = logging.getLogger(__name__)

# Domain choices including concurrency and deployment per Phase 5 spec
DOMAIN_OPTIONS: List[str] = [
    "security",
    "concurrency",
    "data_integrity",
    "performance",
    "deployment",
    "architecture",
    "testing",
    "general",
]

# Priority level options including RFC 2119 equivalent terms
LEVEL_OPTIONS: List[str] = [
    "must",
    "should",
    "forbidden",
    "must_not",
]

# Mapping domains to canonical ParsedConstraintCategory
DOMAIN_CATEGORY_MAP: Dict[str, ParsedConstraintCategory] = {
    "security": ParsedConstraintCategory.SECURITY,
    "concurrency": ParsedConstraintCategory.PERFORMANCE,
    "performance": ParsedConstraintCategory.PERFORMANCE,
    "data_integrity": ParsedConstraintCategory.DATA_INTEGRITY,
    "deployment": ParsedConstraintCategory.ARCHITECTURE,
    "architecture": ParsedConstraintCategory.ARCHITECTURE,
    "testing": ParsedConstraintCategory.TESTING,
    "general": ParsedConstraintCategory.GENERAL,
}

# Mapping level strings to canonical ParsedConstraintLevel
LEVEL_MAP: Dict[str, ParsedConstraintLevel] = {
    "must": ParsedConstraintLevel.MUST,
    "should": ParsedConstraintLevel.SHOULD,
    "forbidden": ParsedConstraintLevel.MUST_NOT,
    "must_not": ParsedConstraintLevel.MUST_NOT,
}

# Concurrency and deployment regex patterns for domain disambiguation
CONCURRENCY_PATTERN = re.compile(
    r"\b(?:concurren\w*|thread\w*|mutex\w*|locks?|deadlock\w*|race condition\w*|atomic\w*|goroutine\w*|worker pool|thread safety)\b",
    re.IGNORECASE,
)
DEPLOYMENT_PATTERN = re.compile(
    r"\b(?:deploy\w*|docker\w*|container\w*|kubernetes|k8s|pod\w*|helm|ci/cd|pipeline\w*|production rollout|artifact|release)\b",
    re.IGNORECASE,
)

# Rule prefix triggers
EXPLICIT_RULE_PREFIX = re.compile(
    r"^(?:rule|invariant|constraint|requirement|policy|guideline|directive)\s*[:\-]",
    re.IGNORECASE,
)

# Strong imperative obligation verbs
IMPERATIVE_VERBS = re.compile(
    r"\b(?:ensure\w*|enforce\w*|requir\w*|prohibit\w*|disallow\w*|reject\w*|guarantee\w*|prevent\w*|restrict\w*|isolate\w*|bound\w*|strictly|mandatory|always|never|forbidden|sanitiz\w*|validat\w*|encrypt\w*)\b",
    re.IGNORECASE,
)

# Prescriptive universal directives (e.g. "all endpoints require", "every change must")
UNIVERSAL_DIRECTIVES = re.compile(
    r"\b(?:all|every|each|no)\s+[\w\-]+(?:\s+[\w\-]+)?\s+(?:must|shall|should|need to|are required to|have to|cannot|may not)\b",
    re.IGNORECASE,
)

# Category pattern overrides with plural and negative tolerance
SECURITY_PATTERN = re.compile(
    r"\b(?:secur\w*|secrets?|credentials?|tokens?|passwords?|(?:un)?auth\w*|sandbox\w*|sanitiz\w*|cve\w*|vulnerabilit\w*|privilege\w*|tenant isolation|permission\w*|access control|encrypt\w*)\b",
    re.IGNORECASE,
)
PERFORMANCE_PATTERN = re.compile(
    r"\b(?:performan\w*|latenc\w*|throughput|memor\w*|cach\w*|concurren\w*|timeout\w*|scal\w*|async\w*|o\(n\)|bottleneck\w*|slow)\b",
    re.IGNORECASE,
)

# Non-invariant negative patterns (questions, changelog entries, installation commands)
NON_INVARIANT_PATTERNS = [
    re.compile(r"^(?:how to|why does|what is|where to|when should)\b", re.IGNORECASE),
    re.compile(r"\?$", re.IGNORECASE),
    re.compile(r"^(?:fixed|added|updated|released|bumped|deprecated in v)\b", re.IGNORECASE),
    re.compile(
        r"^(?:npm|pip|yarn|pnpm|cargo|docker|git|kubectl|brew|curl)\s+(?:run|install|add|remove|build|push|pull|clone|checkout|commit|exec|test|get|apply|set)\b",
        re.IGNORECASE,
    ),
]


class SemanticInvariantMiner:
    """Mines natural-language architectural invariants using System One and heuristics."""

    def __init__(self, client: Optional[SystemOneClient] = None) -> None:
        self.client = client or SystemOneClient()

    @staticmethod
    def _generate_title(statement: str) -> str:
        """Extract a clean, concise title from the invariant statement."""
        first_clause = re.split(r"[:.]", statement)[0].strip()
        words = first_clause.split()
        if len(words) <= 10 and len(first_clause) >= 5:
            return first_clause
        if len(words) > 10:
            return " ".join(words[:8]) + "..."
        return statement[:80]

    @classmethod
    def heuristic_classify(
        cls, statement: str
    ) -> Tuple[bool, ParsedConstraintCategory, ParsedConstraintLevel, str]:
        """
        Deterministic heuristic classification for candidate statements.
        Returns (is_invariant, category, level, domain_str).
        """
        text = statement.strip()
        lower = text.lower()

        # Check negative filters
        for pat in NON_INVARIANT_PATTERNS:
            if pat.search(text):
                return (
                    False,
                    ParsedConstraintCategory.GENERAL,
                    ParsedConstraintLevel.SHOULD,
                    "general",
                )

        # Check explicit invariant prefixes or imperative patterns
        has_prefix = bool(EXPLICIT_RULE_PREFIX.search(text))
        has_rfc = (
            any(p.search(text) for p in MUST_NOT_PATTERNS)
            or any(p.search(text) for p in MUST_PATTERNS)
            or any(p.search(text) for p in SHOULD_PATTERNS)
        )
        has_imperative = bool(IMPERATIVE_VERBS.search(text))
        has_universal = bool(UNIVERSAL_DIRECTIVES.search(text))
        has_prohibition = bool(
            re.search(
                r"\b(?:strictly forbidden|not allowed|prohibited|disallowed|must not|cannot|do not)\b",
                lower,
            )
        )

        is_inv = has_prefix or has_rfc or has_imperative or has_universal or has_prohibition

        # Determine domain string and category
        domain_str = "general"
        category = ParsedConstraintCategory.GENERAL

        if CONCURRENCY_PATTERN.search(text):
            domain_str = "concurrency"
            category = ParsedConstraintCategory.PERFORMANCE
        elif DEPLOYMENT_PATTERN.search(text):
            domain_str = "deployment"
            category = ParsedConstraintCategory.ARCHITECTURE
        elif SECURITY_PATTERN.search(text):
            domain_str = "security"
            category = ParsedConstraintCategory.SECURITY
        elif CATEGORY_PATTERNS[ParsedConstraintCategory.DATA_INTEGRITY].search(text):
            domain_str = "data_integrity"
            category = ParsedConstraintCategory.DATA_INTEGRITY
        elif PERFORMANCE_PATTERN.search(text):
            domain_str = "performance"
            category = ParsedConstraintCategory.PERFORMANCE
        elif CATEGORY_PATTERNS[ParsedConstraintCategory.TESTING].search(text):
            domain_str = "testing"
            category = ParsedConstraintCategory.TESTING
        elif CATEGORY_PATTERNS[ParsedConstraintCategory.ARCHITECTURE].search(text):
            domain_str = "architecture"
            category = ParsedConstraintCategory.ARCHITECTURE

        # Determine level
        if any(p.search(text) for p in MUST_NOT_PATTERNS) or has_prohibition:
            level = ParsedConstraintLevel.MUST_NOT
        elif any(p.search(text) for p in SHOULD_PATTERNS) or re.search(
            r"\b(?:recommended|preferable|strongly encourage|ought to)\b", lower
        ):
            level = ParsedConstraintLevel.SHOULD
        else:
            level = ParsedConstraintLevel.MUST

        return is_inv, category, level, domain_str

    async def evaluate_statement(
        self, statement: str, source_path: str = ""
    ) -> Optional[ParsedConstraint]:
        """Evaluate a single statement and return ParsedConstraint if invariant, else None."""
        results = await self.mine_document(
            path=source_path,
            content=statement,
            existing_constraints=None,
        )
        return results[0] if results else None

    async def mine_document(
        self,
        path: str,
        content: str,
        existing_constraints: Optional[List[ParsedConstraint]] = None,
        batch_size: int = 20,
    ) -> List[ParsedConstraint]:
        """
        Evaluate candidate sentences from a markdown document and extract verified invariants.
        Deduplicates against already extracted constraints.
        """
        candidates = EngineeringContextParser.extract_candidate_sentences(content)
        if not candidates:
            return []

        # Deduplication sets
        existing_lines: Set[int] = set()
        existing_stmts: Set[str] = set()
        if existing_constraints:
            for ec in existing_constraints:
                if ec.line_start is not None:
                    existing_lines.add(ec.line_start)
                existing_stmts.add(ec.statement.strip().lower())

        # Filter out already indexed candidates
        unindexed: List[Tuple[int, int, str]] = []
        for l_start, l_end, stmt in candidates:
            if l_start in existing_lines:
                continue
            if stmt.strip().lower() in existing_stmts:
                continue
            unindexed.append((l_start, l_end, stmt))

        if not unindexed:
            return []

        mined_constraints: List[ParsedConstraint] = []

        # Process in chunks of batch_size
        for i in range(0, len(unindexed), batch_size):
            chunk = unindexed[i : i + batch_size]
            questions: Dict[str, SystemOneQuestion] = {}
            fallbacks: Dict[str, Any] = {}

            for idx, (_, _, text) in enumerate(chunk):
                q_inv_id = f"q_{idx}_is_inv"
                q_cat_id = f"q_{idx}_category"
                q_lvl_id = f"q_{idx}_level"

                h_inv, h_cat, h_lvl, h_domain = self.heuristic_classify(text)

                questions[q_inv_id] = NoulQuestion(
                    instructions=(
                        f"Evaluate if this statement from '{path}' defines an architectural invariant, "
                        f"engineering rule, security constraint, or non-negotiable system requirement: '{text}'"
                    )
                )
                questions[q_cat_id] = ChoiceQuestion(
                    instructions=(
                        f"Classify the engineering domain for this invariant from '{path}': '{text}'"
                    ),
                    options=DOMAIN_OPTIONS,
                )
                questions[q_lvl_id] = ChoiceQuestion(
                    instructions=(
                        f"Determine the RFC 2119 equivalent requirement level for this rule: '{text}'"
                    ),
                    options=LEVEL_OPTIONS,
                )

                fallbacks[q_inv_id] = h_inv
                fallbacks[q_cat_id] = h_domain
                fallbacks[q_lvl_id] = h_lvl.value

            batch_results = await self.client.evaluate_batch(
                state={"path": path, "candidates_count": len(chunk)},
                questions=questions,
                fallbacks=fallbacks,
            )

            for idx, (l_start, l_end, text) in enumerate(chunk):
                q_inv_id = f"q_{idx}_is_inv"
                q_cat_id = f"q_{idx}_category"
                q_lvl_id = f"q_{idx}_level"

                inv_res = batch_results.get(q_inv_id)
                if not inv_res or not inv_res.value:
                    continue

                cat_res = batch_results.get(q_cat_id)
                lvl_res = batch_results.get(q_lvl_id)

                cat_str = str(cat_res.value).lower() if cat_res else "general"
                lvl_str = str(lvl_res.value).lower() if lvl_res else "must"

                category = DOMAIN_CATEGORY_MAP.get(cat_str, ParsedConstraintCategory.GENERAL)
                level = LEVEL_MAP.get(lvl_str, ParsedConstraintLevel.MUST)

                confidence = inv_res.confidence if inv_res.accepted else 0.85
                title = self._generate_title(text)

                mined_constraints.append(
                    ParsedConstraint(
                        category=category,
                        level=level,
                        title=title,
                        statement=text,
                        source_path=path,
                        line_start=l_start,
                        line_end=l_end,
                        confidence=confidence,
                        extra_metadata={
                            "semantic_mined": True,
                            "domain": cat_str,
                            "source": inv_res.source,
                            "is_invariant_confidence": inv_res.confidence,
                            "category_source": cat_res.source if cat_res else "fallback",
                            "level_source": lvl_res.source if lvl_res else "fallback",
                        },
                    )
                )

        return mined_constraints
