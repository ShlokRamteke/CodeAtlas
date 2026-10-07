"""Git Commit Intent & Defect Fix Classifier.

Classifies git commit messages and change history into semantic intents
(bugfix, refactor, feature, chore, security_patch) and determines defect repair
status (is_defect_fix: noul) using typed System One decision models with
calibrated fallback heuristics.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence

from app.semantic.client import SystemOneClient
from app.semantic.systemone import (
    ChoiceQuestion,
    NoulQuestion,
    SystemOneQuestion,
)

logger = logging.getLogger(__name__)


class CommitIntent(str, Enum):
    """Semantic category of a commit's primary intent."""

    BUGFIX = "bugfix"
    REFACTOR = "refactor"
    FEATURE = "feature"
    CHORE = "chore"
    SECURITY_PATCH = "security_patch"


INTENT_OPTIONS: List[str] = [intent.value for intent in CommitIntent]

# Conventional commit regex: e.g. "feat(auth): add login", "fix!: null pointer", "sec(crypto): patch cve"
CONVENTIONAL_COMMIT_RE = re.compile(
    r"^(?P<type>[a-zA-Z]+)(?:\([^\)]+\))?!?:",
    re.IGNORECASE,
)

# Security patch patterns
SECURITY_PATTERNS = re.compile(
    r"\b(?:cve[-\d]+|vulnerabilit\w*|security\s+(?:patch|fix|update|advisory|issue)|xss|csrf|sql\s+injection|rce|remote\s+code\s+execution|exploit\w*|privilege\s+escalation|dos\b|denial\s+of\s+service|auth(?:n|z)?\s+bypass|memory\s+corruption|buffer\s+overflow)\b",
    re.IGNORECASE,
)

# Bug and defect repair patterns
BUGFIX_PATTERNS = re.compile(
    r"\b(?:fix(?:es|ed|ing)?|bug(?:s|fix)?|defect\w*|regression\w*|repair\w*|resolv(?:e|es|ed|ing)|patch(?:es|ed)?|hotfix\w*|broken|crash(?:es|ed)?|hang(?:s|ed)?|deadlock\w*|race\s+condition|leak\w*|null\s*pointer|nil\s*pointer|exception\w*|error\s*handling|closes?\s+#\d+|fixes?\s+#\d+|resolves?\s+#\d+|revert(?:s|ed)?)\b",
    re.IGNORECASE,
)

# Feature addition patterns
FEATURE_PATTERNS = re.compile(
    r"\b(?:feat(?:ure)?|add(?:s|ed|ing)?|implement(?:s|ed|ing)?|support(?:s|ed|ing)?|introduc(?:e|es|ed|ing)|new\s+[\w\-]+|allow(?:s|ed|ing)?|enable(?:s|d)?)\b",
    re.IGNORECASE,
)

# Refactoring patterns
REFACTOR_PATTERNS = re.compile(
    r"\b(?:refactor\w*|restructur\w*|reorganiz\w*|simplif\w*|clean(?:up)?|moderniz\w*|optimiz\w*|speed\s*up|extract\w*|consolidat\w*|decoupl\w*|renam\w*|rewrit\w*|mov(?:e|ed|ing)\s+[\w/]+)\b",
    re.IGNORECASE,
)

# Chore and maintenance patterns
CHORE_PATTERNS = re.compile(
    r"\b(?:chore\w*|docs?\b|documentation|readme|comment\w*|typo\w*|test(?:s|ing)?|ci\b|cd\b|build\b|deps?\b|dependenc\w*|upgrade\w*|bump\w*|lint\w*|format\w*|style\b|release\b|version\b|workflow\w*)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CommitClassificationResult:
    """Consolidated classification result for a commit."""

    commit_intent: CommitIntent
    is_defect_fix: bool
    intent_confidence: float = 1.0
    defect_confidence: float = 1.0
    source: str = "heuristic"  # "model" or "heuristic"
    intent_raw_answer: Optional[str] = None
    defect_raw_probability: Optional[float] = None
    fallback_reason: Optional[str] = None


class CommitIntentClassifier:
    """Classifies git commits into semantic intents and defect status using System One."""

    def __init__(self, client: Optional[SystemOneClient] = None) -> None:
        self.client = client or SystemOneClient()

    @staticmethod
    def heuristic_classify(
        message: str,
        touched_files: Optional[Sequence[str]] = None,
    ) -> tuple[CommitIntent, bool]:
        """Deterministic heuristic rule fallback for classifying commit intent and defect status."""
        msg = message.strip()
        first_line = msg.splitlines()[0].strip() if msg else ""

        # 1. Conventional commit prefix check
        m = CONVENTIONAL_COMMIT_RE.match(first_line)
        if m:
            prefix = m.group("type").lower()
            if prefix in ("sec", "security"):
                return CommitIntent.SECURITY_PATCH, True
            if prefix in ("fix", "hotfix", "patch", "bug", "revert"):
                return CommitIntent.BUGFIX, True
            if prefix in ("feat", "feature"):
                return CommitIntent.FEATURE, False
            if prefix in ("refactor", "perf", "clean", "rewrite"):
                return CommitIntent.REFACTOR, False
            if prefix in ("chore", "docs", "doc", "test", "tests", "ci", "build", "style"):
                return CommitIntent.CHORE, False

        # 2. Security keyword check across entire message
        if SECURITY_PATTERNS.search(msg):
            return CommitIntent.SECURITY_PATCH, True

        # 3. Bugfix keyword check
        if BUGFIX_PATTERNS.search(msg):
            return CommitIntent.BUGFIX, True

        # 4. Refactor check
        if REFACTOR_PATTERNS.search(msg):
            return CommitIntent.REFACTOR, False

        # 5. Feature check
        if FEATURE_PATTERNS.search(msg):
            return CommitIntent.FEATURE, False

        # 6. Chore check
        if CHORE_PATTERNS.search(msg):
            return CommitIntent.CHORE, False

        # Check touched files heuristic
        if touched_files:
            file_paths = [f.lower() for f in touched_files]
            if all(
                any(doc in f for doc in ("readme", "docs/", ".md", "license", ".txt"))
                for f in file_paths
            ):
                return CommitIntent.CHORE, False
            if all(any(t in f for t in ("test", "tests", "spec", "__tests__")) for f in file_paths):
                return CommitIntent.CHORE, False

        # Default fallback
        return CommitIntent.CHORE, False

    async def classify_commit(
        self,
        message: str,
        commit_hash: str = "",
        touched_files: Optional[Sequence[str]] = None,
    ) -> CommitClassificationResult:
        """Classify a single commit with System One model and calibrated fallback."""
        fb_intent, fb_defect = self.heuristic_classify(message, touched_files)

        state = {
            "commit_hash": commit_hash,
            "message": message,
            "touched_files": list(touched_files or [])[:10],
        }

        q_intent_id = f"intent_{commit_hash or '0'}"
        q_defect_id = f"defect_{commit_hash or '0'}"

        questions: Dict[str, SystemOneQuestion] = {
            q_intent_id: ChoiceQuestion(
                instructions=(
                    f"Classify the primary intent of this git commit message: '{message}'. "
                    "Options: bugfix, refactor, feature, chore, security_patch."
                ),
                options=INTENT_OPTIONS,
            ),
            q_defect_id: NoulQuestion(
                instructions=(
                    f"Does this git commit repair or resolve a software defect, bug, regression, or vulnerability: '{message}'?"
                )
            ),
        }

        fallbacks: Dict[str, Any] = {
            q_intent_id: fb_intent.value,
            q_defect_id: fb_defect,
        }

        batch_res = await self.client.evaluate_batch(
            state=state,
            questions=questions,
            fallbacks=fallbacks,
        )

        intent_res = batch_res.get(q_intent_id)
        defect_res = batch_res.get(q_defect_id)

        # Parse intent
        final_intent = fb_intent
        intent_conf = 1.0
        intent_source = "heuristic"
        intent_raw = None
        fallback_reason = None

        if intent_res:
            intent_conf = intent_res.confidence
            intent_raw = intent_res.raw_answer
            fallback_reason = intent_res.fallback_reason
            if intent_res.accepted and intent_res.source == "model":
                try:
                    final_intent = CommitIntent(str(intent_res.value))
                    intent_source = "model"
                except ValueError:
                    final_intent = fb_intent

        # Parse defect fix
        final_defect = fb_defect
        defect_conf = 1.0
        defect_raw_prob = None

        if defect_res:
            defect_conf = defect_res.confidence
            if defect_res.accepted and defect_res.source == "model":
                try:
                    val = defect_res.value
                    if isinstance(val, bool):
                        final_defect = val
                    elif isinstance(val, (int, float)):
                        final_defect = float(val) >= 0.5
                        defect_raw_prob = float(val)
                    elif str(val).lower() in ("true", "yes", "1"):
                        final_defect = True
                    else:
                        final_defect = False
                except Exception:
                    final_defect = fb_defect
            else:
                final_defect = fb_defect

        # Harmonize: if intent is bugfix or security_patch, mark is_defect_fix
        if final_intent in (CommitIntent.BUGFIX, CommitIntent.SECURITY_PATCH):
            final_defect = True

        overall_source = (
            "model"
            if (intent_source == "model" or (defect_res and defect_res.source == "model"))
            else "heuristic"
        )

        return CommitClassificationResult(
            commit_intent=final_intent,
            is_defect_fix=final_defect,
            intent_confidence=intent_conf,
            defect_confidence=defect_conf,
            source=overall_source,
            intent_raw_answer=intent_raw,
            defect_raw_probability=defect_raw_prob,
            fallback_reason=fallback_reason,
        )

    async def classify_commits_batch(
        self,
        commits: Sequence[Dict[str, Any] | Any],
    ) -> Dict[str, CommitClassificationResult]:
        """Batch classify multiple commits in a single forward pass."""
        if not commits:
            return {}

        questions: Dict[str, SystemOneQuestion] = {}
        fallbacks: Dict[str, Any] = {}
        meta_by_hash: Dict[str, Dict[str, Any]] = {}
        commit_states: List[Dict[str, Any]] = []

        for idx, item in enumerate(commits):
            if isinstance(item, dict):
                c_hash = str(item.get("commit_hash") or f"c_{idx}")
                msg = str(item.get("message") or "")
                touched = item.get("touched_files") or []
            else:
                c_hash = getattr(item, "commit_hash", f"c_{idx}")
                msg = getattr(item, "message", "")
                file_changes = getattr(item, "file_changes", [])
                touched = [getattr(fc, "file_path", str(fc)) for fc in file_changes]

            fb_intent, fb_defect = self.heuristic_classify(msg, touched)

            q_intent_id = f"intent_{c_hash}"
            q_defect_id = f"defect_{c_hash}"

            questions[q_intent_id] = ChoiceQuestion(
                instructions=(
                    f"Classify commit '{msg}'. Options: bugfix, refactor, feature, chore, security_patch."
                ),
                options=INTENT_OPTIONS,
            )
            questions[q_defect_id] = NoulQuestion(
                instructions=f"Does commit '{msg}' repair a software defect, bug, regression, or vulnerability?"
            )

            fallbacks[q_intent_id] = fb_intent.value
            fallbacks[q_defect_id] = fb_defect

            meta_by_hash[c_hash] = {
                "fb_intent": fb_intent,
                "fb_defect": fb_defect,
                "q_intent_id": q_intent_id,
                "q_defect_id": q_defect_id,
            }

            commit_states.append(
                {
                    "commit_hash": c_hash,
                    "message": msg,
                    "touched_files": list(touched)[:10],
                }
            )

        state = {"commits": commit_states}

        batch_res = await self.client.evaluate_batch(
            state=state,
            questions=questions,
            fallbacks=fallbacks,
        )

        results: Dict[str, CommitClassificationResult] = {}

        for c_hash, meta in meta_by_hash.items():
            fb_intent = meta["fb_intent"]
            fb_defect = meta["fb_defect"]
            q_intent_id = meta["q_intent_id"]
            q_defect_id = meta["q_defect_id"]

            intent_res = batch_res.get(q_intent_id)
            defect_res = batch_res.get(q_defect_id)

            final_intent = fb_intent
            intent_conf = 1.0
            intent_source = "heuristic"
            intent_raw = None
            fallback_reason = None

            if intent_res:
                intent_conf = intent_res.confidence
                intent_raw = intent_res.raw_answer
                fallback_reason = intent_res.fallback_reason
                if intent_res.accepted and intent_res.source == "model":
                    try:
                        final_intent = CommitIntent(str(intent_res.value))
                        intent_source = "model"
                    except ValueError:
                        final_intent = fb_intent

            final_defect = fb_defect
            defect_conf = 1.0
            defect_raw_prob = None

            if defect_res:
                defect_conf = defect_res.confidence
                if defect_res.accepted and defect_res.source == "model":
                    try:
                        val = defect_res.value
                        if isinstance(val, bool):
                            final_defect = val
                        elif isinstance(val, (int, float)):
                            final_defect = float(val) >= 0.5
                            defect_raw_prob = float(val)
                        elif str(val).lower() in ("true", "yes", "1"):
                            final_defect = True
                        else:
                            final_defect = False
                    except Exception:
                        final_defect = fb_defect

            if final_intent in (CommitIntent.BUGFIX, CommitIntent.SECURITY_PATCH):
                final_defect = True

            overall_source = (
                "model"
                if (intent_source == "model" or (defect_res and defect_res.source == "model"))
                else "heuristic"
            )

            results[c_hash] = CommitClassificationResult(
                commit_intent=final_intent,
                is_defect_fix=final_defect,
                intent_confidence=intent_conf,
                defect_confidence=defect_conf,
                source=overall_source,
                intent_raw_answer=intent_raw,
                defect_raw_probability=defect_raw_prob,
                fallback_reason=fallback_reason,
            )

        return results
