"""Semantic Indexing & System One Decision Engine.

Provides typed, sub-40ms non-autoregressive decision models (/v1/systemone)
for architectural role classification, invariant extraction, commit intent mining,
and C4 container boundary detection with calibrated fallback.
"""

from __future__ import annotations

from app.semantic.client import MockSystemOneClient, SystemOneClient
from app.semantic.systemone import (
    ChoiceAnswer,
    ChoiceQuestion,
    DecisionResult,
    NoulAnswer,
    NoulQuestion,
    QuestionType,
    ScoreAnswer,
    ScoreQuestion,
    SystemOneAnswer,
    SystemOneQuestion,
    SystemOneRequest,
    SystemOneResponse,
    SystemOneUsage,
)

__all__ = [
    "ChoiceAnswer",
    "ChoiceQuestion",
    "DecisionResult",
    "MockSystemOneClient",
    "NoulAnswer",
    "NoulQuestion",
    "QuestionType",
    "ScoreAnswer",
    "ScoreQuestion",
    "SystemOneAnswer",
    "SystemOneClient",
    "SystemOneQuestion",
    "SystemOneRequest",
    "SystemOneResponse",
    "SystemOneUsage",
]
