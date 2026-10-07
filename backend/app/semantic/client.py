"""System One Client and Calibrated Protocol Adapter.

Connects to non-autoregressive decision model servers implementing /v1/systemone.
Provides calibrated probability parsing, strict confidence gating (>= 0.85),
deterministic fallbacks, and a mock provider for fast offline unit testing.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

import httpx

from app.core.config import settings
from app.semantic.systemone import (
    ChoiceAnswer,
    ChoiceQuestion,
    DecisionResult,
    NoulAnswer,
    NoulQuestion,
    ScoreAnswer,
    ScoreQuestion,
    SystemOneAnswer,
    SystemOneQuestion,
    SystemOneRequest,
    SystemOneResponse,
)

logger = logging.getLogger(__name__)


class SystemOneClient:
    """Async client for /v1/systemone decision models with calibrated fallback."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
        enabled: bool | None = None,
        confidence_threshold: float | None = None,
        model: str = "laya-latest",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = (base_url or settings.DECISION_MODEL_URL).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.DECISION_MODEL_TIMEOUT
        self.enabled = enabled if enabled is not None else settings.DECISION_MODEL_ENABLED
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else settings.DECISION_CONFIDENCE_THRESHOLD
        )
        self.model = model
        self._http_client = http_client

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is not None:
            return self._http_client
        return httpx.AsyncClient(timeout=self.timeout)

    async def ask(self, request: SystemOneRequest) -> SystemOneResponse:
        """Issue raw wire request to POST /v1/systemone."""
        endpoint = f"{self.base_url}/v1/systemone"
        payload = request.model_dump()

        client = await self._get_client()
        should_close = self._http_client is None
        try:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
            return SystemOneResponse.model_validate(response.json())
        finally:
            if should_close:
                await client.aclose()

    async def check_health(self) -> bool:
        """Check if System One decision model server is reachable and healthy."""
        if not self.enabled:
            return False
        client = await self._get_client()
        should_close = self._http_client is None
        try:
            response = await client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception:
            return False
        finally:
            if should_close:
                await client.aclose()

    async def decide_noul(
        self,
        state: Any,
        instructions: str,
        fallback: bool,
        threshold: float | None = None,
        question_id: str = "q_noul",
    ) -> DecisionResult[bool]:
        """Evaluate a boolean yes/no question with calibrated certainty gating."""
        target_threshold = threshold if threshold is not None else self.confidence_threshold

        if not self.enabled:
            return DecisionResult(
                accepted=False,
                value=fallback,
                confidence=0.0,
                source="fallback",
                fallback_reason="client_disabled",
            )

        question = NoulQuestion(instructions=instructions)
        request = SystemOneRequest(
            model=self.model,
            state=state,
            questions={question_id: question},
        )

        try:
            response = await self.ask(request)
            raw_ans = response.answers.get(question_id)
            if not isinstance(raw_ans, NoulAnswer):
                return DecisionResult(
                    accepted=False,
                    value=fallback,
                    confidence=0.0,
                    source="fallback",
                    raw_answer=raw_ans,
                    fallback_reason="missing_or_invalid_answer_type",
                )

            certainty = raw_ans.certainty
            if certainty >= target_threshold:
                return DecisionResult(
                    accepted=True,
                    value=raw_ans.boolean_value,
                    confidence=certainty,
                    source="model",
                    raw_answer=raw_ans,
                )
            return DecisionResult(
                accepted=False,
                value=fallback,
                confidence=certainty,
                source="fallback",
                raw_answer=raw_ans,
                fallback_reason=f"confidence_{certainty:.3f}_below_threshold_{target_threshold:.3f}",
            )
        except Exception as exc:
            logger.warning("SystemOne noul decision failed, invoking fallback: %s", exc)
            return DecisionResult(
                accepted=False,
                value=fallback,
                confidence=0.0,
                source="fallback",
                fallback_reason=f"error_{type(exc).__name__}: {exc}",
            )

    async def decide_choice(
        self,
        state: Any,
        instructions: str,
        options: list[str],
        fallback: str,
        threshold: float | None = None,
        question_id: str = "q_choice",
    ) -> DecisionResult[str]:
        """Evaluate categorical choice with calibrated confidence gating."""
        target_threshold = threshold if threshold is not None else self.confidence_threshold

        if not self.enabled:
            return DecisionResult(
                accepted=False,
                value=fallback,
                confidence=0.0,
                source="fallback",
                fallback_reason="client_disabled",
            )

        question = ChoiceQuestion(instructions=instructions, options=options)
        request = SystemOneRequest(
            model=self.model,
            state=state,
            questions={question_id: question},
        )

        try:
            response = await self.ask(request)
            raw_ans = response.answers.get(question_id)
            if not isinstance(raw_ans, ChoiceAnswer):
                return DecisionResult(
                    accepted=False,
                    value=fallback,
                    confidence=0.0,
                    source="fallback",
                    raw_answer=raw_ans,
                    fallback_reason="missing_or_invalid_answer_type",
                )

            if raw_ans.choice not in options:
                return DecisionResult(
                    accepted=False,
                    value=fallback,
                    confidence=raw_ans.confidence,
                    source="fallback",
                    raw_answer=raw_ans,
                    fallback_reason=f"choice_{raw_ans.choice}_not_in_options",
                )

            if raw_ans.confidence >= target_threshold:
                return DecisionResult(
                    accepted=True,
                    value=raw_ans.choice,
                    confidence=raw_ans.confidence,
                    source="model",
                    raw_answer=raw_ans,
                )
            return DecisionResult(
                accepted=False,
                value=fallback,
                confidence=raw_ans.confidence,
                source="fallback",
                raw_answer=raw_ans,
                fallback_reason=f"confidence_{raw_ans.confidence:.3f}_below_threshold_{target_threshold:.3f}",
            )
        except Exception as exc:
            logger.warning("SystemOne choice decision failed, invoking fallback: %s", exc)
            return DecisionResult(
                accepted=False,
                value=fallback,
                confidence=0.0,
                source="fallback",
                fallback_reason=f"error_{type(exc).__name__}: {exc}",
            )

    async def decide_score(
        self,
        state: Any,
        instructions: str,
        legend: list[str],
        fallback: float,
        threshold: float | None = None,
        question_id: str = "q_score",
    ) -> DecisionResult[float]:
        """Evaluate continuous/ordinal score rating with confidence gating."""
        target_threshold = threshold if threshold is not None else self.confidence_threshold

        if not self.enabled:
            return DecisionResult(
                accepted=False,
                value=fallback,
                confidence=0.0,
                source="fallback",
                fallback_reason="client_disabled",
            )

        question = ScoreQuestion(instructions=instructions, legend=legend)
        request = SystemOneRequest(
            model=self.model,
            state=state,
            questions={question_id: question},
        )

        try:
            response = await self.ask(request)
            raw_ans = response.answers.get(question_id)
            if not isinstance(raw_ans, ScoreAnswer):
                return DecisionResult(
                    accepted=False,
                    value=fallback,
                    confidence=0.0,
                    source="fallback",
                    raw_answer=raw_ans,
                    fallback_reason="missing_or_invalid_answer_type",
                )

            if raw_ans.confidence >= target_threshold:
                return DecisionResult(
                    accepted=True,
                    value=raw_ans.score,
                    confidence=raw_ans.confidence,
                    source="model",
                    raw_answer=raw_ans,
                )
            return DecisionResult(
                accepted=False,
                value=fallback,
                confidence=raw_ans.confidence,
                source="fallback",
                raw_answer=raw_ans,
                fallback_reason=f"confidence_{raw_ans.confidence:.3f}_below_threshold_{target_threshold:.3f}",
            )
        except Exception as exc:
            logger.warning("SystemOne score decision failed, invoking fallback: %s", exc)
            return DecisionResult(
                accepted=False,
                value=fallback,
                confidence=0.0,
                source="fallback",
                fallback_reason=f"error_{type(exc).__name__}: {exc}",
            )

    async def evaluate_batch(
        self,
        state: Any,
        questions: dict[str, SystemOneQuestion],
        fallbacks: dict[str, Any],
        threshold: float | None = None,
    ) -> dict[str, DecisionResult[Any]]:
        """Evaluate a batch of heterogeneous questions in a single forward pass."""
        target_threshold = threshold if threshold is not None else self.confidence_threshold
        results: dict[str, DecisionResult[Any]] = {}

        if not self.enabled:
            for q_id, fb in fallbacks.items():
                results[q_id] = DecisionResult(
                    accepted=False,
                    value=fb,
                    confidence=0.0,
                    source="fallback",
                    fallback_reason="client_disabled",
                )
            return results

        request = SystemOneRequest(
            model=self.model,
            state=state,
            questions=questions,
        )

        try:
            response = await self.ask(request)
            for q_id, q_spec in questions.items():
                fb = fallbacks.get(q_id)
                ans = response.answers.get(q_id)

                if ans is None:
                    results[q_id] = DecisionResult(
                        accepted=False,
                        value=fb,
                        confidence=0.0,
                        source="fallback",
                        fallback_reason="question_id_not_in_response",
                    )
                elif isinstance(ans, NoulAnswer):
                    cert = ans.certainty
                    if cert >= target_threshold:
                        results[q_id] = DecisionResult(
                            accepted=True,
                            value=ans.boolean_value,
                            confidence=cert,
                            source="model",
                            raw_answer=ans,
                        )
                    else:
                        results[q_id] = DecisionResult(
                            accepted=False,
                            value=fb,
                            confidence=cert,
                            source="fallback",
                            raw_answer=ans,
                            fallback_reason=f"confidence_{cert:.3f}_below_threshold_{target_threshold:.3f}",
                        )
                elif isinstance(ans, ChoiceAnswer):
                    options = getattr(q_spec, "options", [])
                    if options and ans.choice not in options:
                        results[q_id] = DecisionResult(
                            accepted=False,
                            value=fb,
                            confidence=ans.confidence,
                            source="fallback",
                            raw_answer=ans,
                            fallback_reason=f"choice_{ans.choice}_not_in_options",
                        )
                    elif ans.confidence >= target_threshold:
                        results[q_id] = DecisionResult(
                            accepted=True,
                            value=ans.choice,
                            confidence=ans.confidence,
                            source="model",
                            raw_answer=ans,
                        )
                    else:
                        results[q_id] = DecisionResult(
                            accepted=False,
                            value=fb,
                            confidence=ans.confidence,
                            source="fallback",
                            raw_answer=ans,
                            fallback_reason=f"confidence_{ans.confidence:.3f}_below_threshold_{target_threshold:.3f}",
                        )
                elif isinstance(ans, ScoreAnswer):
                    if ans.confidence >= target_threshold:
                        results[q_id] = DecisionResult(
                            accepted=True,
                            value=ans.score,
                            confidence=ans.confidence,
                            source="model",
                            raw_answer=ans,
                        )
                    else:
                        results[q_id] = DecisionResult(
                            accepted=False,
                            value=fb,
                            confidence=ans.confidence,
                            source="fallback",
                            raw_answer=ans,
                            fallback_reason=f"confidence_{ans.confidence:.3f}_below_threshold_{target_threshold:.3f}",
                        )
                else:
                    results[q_id] = DecisionResult(
                        accepted=False,
                        value=fb,
                        confidence=0.0,
                        source="fallback",
                        raw_answer=ans,
                        fallback_reason="unsupported_answer_type",
                    )
            return results
        except Exception as exc:
            logger.warning("SystemOne batch evaluation failed, falling back: %s", exc)
            for q_id, fb in fallbacks.items():
                results[q_id] = DecisionResult(
                    accepted=False,
                    value=fb,
                    confidence=0.0,
                    source="fallback",
                    fallback_reason=f"error_{type(exc).__name__}: {exc}",
                )
            return results


class MockSystemOneClient(SystemOneClient):
    """In-memory mock decision client for fast deterministic unit & CI testing."""

    def __init__(
        self,
        responses: dict[str, SystemOneAnswer] | None = None,
        handler: Callable[[str, SystemOneQuestion, Any], SystemOneAnswer | None] | None = None,
        offline: bool = False,
        confidence_threshold: float = 0.85,
        enabled: bool = True,
    ) -> None:
        super().__init__(
            base_url="http://mock-systemone:8081",
            confidence_threshold=confidence_threshold,
            enabled=enabled,
        )
        self.preset_responses: dict[str, SystemOneAnswer] = responses or {}
        self.handler = handler
        self.offline = offline

    def set_response(self, question_id: str, answer: SystemOneAnswer) -> None:
        """Register a canned answer for a specific question ID."""
        self.preset_responses[question_id] = answer

    def set_noul_response(self, question_id: str, noul: float) -> None:
        """Register a canned boolean/noul probability answer."""
        self.preset_responses[question_id] = NoulAnswer(noul=noul)

    def set_choice_response(
        self,
        question_id: str,
        choice: str,
        confidence: float = 0.95,
        probabilities: dict[str, float] | None = None,
    ) -> None:
        """Register a canned categorical choice answer."""
        probs = probabilities or {choice: confidence}
        self.preset_responses[question_id] = ChoiceAnswer(
            choice=choice,
            confidence=confidence,
            probabilities=probs,
        )

    def set_score_response(
        self,
        question_id: str,
        score: float,
        confidence: float = 0.95,
        legend: list[str] | None = None,
    ) -> None:
        """Register a canned score answer."""
        self.preset_responses[question_id] = ScoreAnswer(
            score=score,
            confidence=confidence,
            legend=legend or ["low", "high"],
        )

    def set_offline(self, offline: bool = True) -> None:
        """Simulate network disconnection."""
        self.offline = offline

    async def check_health(self) -> bool:
        """Check mock decision server availability."""
        return not self.offline and self.enabled

    async def ask(self, request: SystemOneRequest) -> SystemOneResponse:
        """Process request against registered canned responses or dynamic handler."""
        if self.offline:
            raise httpx.ConnectError(
                "Mock System One server is offline (simulated connection failure)"
            )

        answers: dict[str, SystemOneAnswer] = {}
        for q_id, q_spec in request.questions.items():
            if q_id in self.preset_responses:
                answers[q_id] = self.preset_responses[q_id]
            elif self.handler is not None:
                handled = self.handler(q_id, q_spec, request.state)
                if handled is not None:
                    answers[q_id] = handled

        return SystemOneResponse(
            model=request.model,
            answers=answers,
        )
