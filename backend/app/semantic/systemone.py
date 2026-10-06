"""System One (/v1/systemone) Protocol & Schema Definitions.

Implements the typed, non-autoregressive decision model protocol:
- choice: categorical classification over defined options
- noul: boolean yes/no probabilistic assessment
- score: ordered numeric evaluation with scale legend
"""

from __future__ import annotations

from typing import Annotated, Any, Generic, Literal, TypeVar, Union

from pydantic import BaseModel, Field

QuestionType = Literal["noul", "choice", "score"]


class NoulQuestion(BaseModel):
    """Boolean yes/no question returning a probability in [0, 1]."""

    type: Literal["noul"] = "noul"
    instructions: str


class ChoiceQuestion(BaseModel):
    """Categorical question selecting from discrete options."""

    type: Literal["choice"] = "choice"
    instructions: str
    options: list[str] = Field(min_length=1)


class ScoreQuestion(BaseModel):
    """Continuous or discrete rating against an ordered scale."""

    type: Literal["score"] = "score"
    instructions: str
    legend: list[str] = Field(min_length=2)


SystemOneQuestion = Annotated[
    Union[NoulQuestion, ChoiceQuestion, ScoreQuestion],
    Field(discriminator="type"),
]


class NoulAnswer(BaseModel):
    """Answer for a noul question containing raw probability of 'yes'."""

    type: Literal["noul"] = "noul"
    noul: float = Field(ge=0.0, le=1.0)

    @property
    def certainty(self) -> float:
        """Calibrated certainty distance from 0.5 uncertainty."""
        return max(self.noul, 1.0 - self.noul)

    @property
    def boolean_value(self) -> bool:
        """Binary resolution above 0.5 midpoint."""
        return self.noul >= 0.5


class ChoiceAnswer(BaseModel):
    """Answer for a choice question with distribution and top confidence."""

    type: Literal["choice"] = "choice"
    choice: str
    probabilities: dict[str, float] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)


class ScoreAnswer(BaseModel):
    """Answer for a score question with numeric score and confidence."""

    type: Literal["score"] = "score"
    score: float
    confidence: float = Field(ge=0.0, le=1.0)
    legend: list[str] = Field(default_factory=list)


SystemOneAnswer = Annotated[
    Union[NoulAnswer, ChoiceAnswer, ScoreAnswer],
    Field(discriminator="type"),
]


class SystemOneUsage(BaseModel):
    """Token telemetry reported by System One runtime."""

    input_tokens: int = 0
    output_tokens: int = 0


class SystemOneRequest(BaseModel):
    """Wire request payload for POST /v1/systemone."""

    model: str = "laya-latest"
    state: Any
    questions: dict[str, SystemOneQuestion]


class SystemOneResponse(BaseModel):
    """Wire response payload from POST /v1/systemone."""

    model: str
    answers: dict[str, SystemOneAnswer]
    usage: SystemOneUsage | None = None


T = TypeVar("T")


class DecisionResult(BaseModel, Generic[T]):
    """Calibrated decision outcome with deterministic fallback traceability."""

    accepted: bool
    value: T
    confidence: float
    source: Literal["model", "fallback"]
    raw_answer: SystemOneAnswer | None = None
    fallback_reason: str | None = None
