"""Architectural Symbol Role Classifier.

Classifies class, function, and interface symbols into architectural roles
(controller, service, repository, entity, middleware, utility) using fast,
typed System One decision models with deterministic fallback heuristics.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.models.symbol import ArchitecturalRole
from app.parser.ast_parser import ExtractedSymbol
from app.semantic.client import SystemOneClient
from app.semantic.systemone import ChoiceQuestion, DecisionResult

logger = logging.getLogger(__name__)

ROLE_OPTIONS: List[str] = [role.value for role in ArchitecturalRole]


class SymbolRoleClassifier:
    """Classifies architectural roles of code symbols using System One with heuristic fallback."""

    def __init__(self, client: Optional[SystemOneClient] = None) -> None:
        self.client = client or SystemOneClient()

    @staticmethod
    def heuristic_classify(
        name: str,
        file_path: str,
        kind: str = "function",
        decorators: Optional[List[str]] = None,
        method_names: Optional[List[str]] = None,
        docstring: Optional[str] = None,
    ) -> ArchitecturalRole:
        """Deterministic heuristic rule fallback for classifying a symbol's architectural role."""
        name_lower = name.lower()
        path_lower = file_path.lower().replace("\\", "/")
        decorators_lower = [d.lower() for d in (decorators or [])]
        method_names_lower = [m.lower() for m in (method_names or [])]
        doc_lower = (docstring or "").lower()

        # 1. Controller indicators
        is_controller = (
            any(
                part in path_lower
                for part in [
                    "/controller",
                    "/controllers/",
                    "/api/",
                    "/endpoints/",
                    "/routes/",
                    "/routers/",
                    "/views/",
                ]
            )
            or any(
                name_lower.endswith(sfx)
                for sfx in [
                    "controller",
                    "handler",
                    "router",
                    "endpoint",
                    "view",
                    "resource",
                ]
            )
            or any(
                any(
                    kw in dec
                    for kw in [
                        "router.",
                        "app.",
                        "controller",
                        "get(",
                        "post(",
                        "put(",
                        "delete(",
                        "patch(",
                    ]
                )
                for dec in decorators_lower
            )
        )
        if is_controller:
            return ArchitecturalRole.CONTROLLER

        # 2. Repository indicators
        is_repository = (
            any(
                part in path_lower
                for part in [
                    "/repository",
                    "/repositories/",
                    "/dao/",
                    "/dal/",
                    "/store/",
                    "/stores/",
                ]
            )
            or any(
                name_lower.endswith(sfx)
                for sfx in ["repository", "repo", "dao", "dal", "store", "gateway"]
            )
            or (
                kind == "class"
                and any(
                    any(
                        m.startswith(pfx)
                        for pfx in ["find_by", "get_by", "save", "delete_by", "query_"]
                    )
                    for m in method_names_lower
                )
            )
        )
        if is_repository:
            return ArchitecturalRole.REPOSITORY

        # 3. Middleware indicators
        is_middleware = any(
            part in path_lower
            for part in ["/middleware", "/middlewares/", "/interceptors/", "/guards/", "/filters/"]
        ) or any(
            name_lower.endswith(sfx) for sfx in ["middleware", "interceptor", "guard", "filter"]
        )
        if is_middleware:
            return ArchitecturalRole.MIDDLEWARE

        # 4. Entity indicators
        is_entity = (
            any(
                part in path_lower
                for part in [
                    "/models/",
                    "/model/",
                    "/entities/",
                    "/entity/",
                    "/schemas/",
                    "/schema/",
                    "/dto/",
                    "/dtos/",
                    "/types/",
                ]
            )
            or any(
                name_lower.endswith(sfx)
                for sfx in [
                    "entity",
                    "model",
                    "schema",
                    "dto",
                    "record",
                    "document",
                    "item",
                    "payload",
                ]
            )
            or any(
                "dataclass" in dec or "entity" in dec or "table" in dec for dec in decorators_lower
            )
            or (
                kind in ["interface", "type"]
                and not any(p in path_lower for p in ["/util", "/lib", "/helpers"])
            )
        )
        if is_entity:
            return ArchitecturalRole.ENTITY

        # 5. Service indicators
        is_service = (
            any(
                part in path_lower
                for part in [
                    "/service",
                    "/services/",
                    "/use_case",
                    "/usecases/",
                    "/interactor",
                    "/domain/",
                    "/business/",
                ]
            )
            or any(
                name_lower.endswith(sfx)
                for sfx in [
                    "service",
                    "manager",
                    "usecase",
                    "use_case",
                    "processor",
                    "interactor",
                    "orchestrator",
                    "engine",
                    "pipeline",
                ]
            )
            or "service" in doc_lower
        )
        if is_service:
            return ArchitecturalRole.SERVICE

        # 6. Utility indicators
        is_utility = any(
            part in path_lower
            for part in [
                "/util",
                "/utils/",
                "/helper",
                "/helpers/",
                "/common/",
                "/shared/",
                "/tools/",
            ]
        ) or any(
            name_lower.endswith(sfx)
            for sfx in ["util", "utils", "helper", "formatter", "parser", "converter", "validator"]
        )
        if is_utility:
            return ArchitecturalRole.UTILITY

        # Default fallback: class -> service/entity, function -> utility
        if kind == "class":
            return ArchitecturalRole.SERVICE
        return ArchitecturalRole.UTILITY

    async def classify_symbol(
        self,
        symbol: ExtractedSymbol | Dict[str, Any],
        file_path: str,
    ) -> DecisionResult[ArchitecturalRole]:
        """Classify a single symbol with System One decision model and calibrated fallback."""
        name = symbol.name if isinstance(symbol, ExtractedSymbol) else str(symbol.get("name", ""))
        kind = (
            symbol.kind
            if isinstance(symbol, ExtractedSymbol)
            else str(symbol.get("kind", "function"))
        )
        signature = (
            symbol.signature if isinstance(symbol, ExtractedSymbol) else symbol.get("signature")
        )
        docstring = (
            symbol.docstring if isinstance(symbol, ExtractedSymbol) else symbol.get("docstring")
        )
        decorators = (
            symbol.decorators
            if isinstance(symbol, ExtractedSymbol)
            else symbol.get("decorators", [])
        )
        method_names = (
            symbol.method_names
            if isinstance(symbol, ExtractedSymbol)
            else symbol.get("method_names", [])
        )

        fallback_role = self.heuristic_classify(
            name=name,
            file_path=file_path,
            kind=kind,
            decorators=decorators,
            method_names=method_names,
            docstring=docstring,
        )

        state = {
            "name": name,
            "kind": kind,
            "file_path": file_path,
            "signature": signature,
            "docstring": docstring,
            "decorators": decorators,
            "method_names": method_names,
        }

        instructions = (
            f"Classify architectural role for code symbol '{name}' ({kind}) in '{file_path}'. "
            "Choose exactly one from options: controller, service, repository, entity, middleware, utility."
        )

        raw_result = await self.client.decide_choice(
            state=state,
            instructions=instructions,
            options=ROLE_OPTIONS,
            fallback=fallback_role.value,
            question_id="architectural_role",
        )

        try:
            role_val = ArchitecturalRole(raw_result.value)
        except ValueError:
            role_val = fallback_role

        return DecisionResult(
            accepted=raw_result.accepted,
            value=role_val,
            confidence=raw_result.confidence,
            source=raw_result.source,
            raw_answer=raw_result.raw_answer,
            fallback_reason=raw_result.fallback_reason,
        )

    async def classify_symbols_batch(
        self,
        symbols: List[ExtractedSymbol | Dict[str, Any]],
        file_path: str,
    ) -> Dict[str, DecisionResult[ArchitecturalRole]]:
        """
        Batch classify symbols in a file using a single System One forward evaluation.
        Falls back gracefully per-symbol on failure, disconnection, or low confidence (< 0.85).
        """
        if not symbols:
            return {}

        results: Dict[str, DecisionResult[ArchitecturalRole]] = {}
        questions: Dict[str, ChoiceQuestion] = {}
        fallbacks: Dict[str, str] = {}
        state_symbols: List[Dict[str, Any]] = []

        for idx, sym in enumerate(symbols):
            q_id = (
                f"q_{idx}_{sym.name if isinstance(sym, ExtractedSymbol) else sym.get('name', idx)}"
            )
            name = sym.name if isinstance(sym, ExtractedSymbol) else str(sym.get("name", ""))
            kind = (
                sym.kind if isinstance(sym, ExtractedSymbol) else str(sym.get("kind", "function"))
            )
            signature = sym.signature if isinstance(sym, ExtractedSymbol) else sym.get("signature")
            docstring = sym.docstring if isinstance(sym, ExtractedSymbol) else sym.get("docstring")
            decorators = (
                sym.decorators if isinstance(sym, ExtractedSymbol) else sym.get("decorators", [])
            )
            method_names = (
                sym.method_names
                if isinstance(sym, ExtractedSymbol)
                else sym.get("method_names", [])
            )

            fb_role = self.heuristic_classify(
                name=name,
                file_path=file_path,
                kind=kind,
                decorators=decorators,
                method_names=method_names,
                docstring=docstring,
            )
            fallbacks[q_id] = fb_role.value

            questions[q_id] = ChoiceQuestion(
                instructions=(
                    f"Classify architectural role of symbol '{name}' ({kind}) in '{file_path}'. "
                    "Options: controller, service, repository, entity, middleware, utility."
                ),
                options=ROLE_OPTIONS,
            )

            state_symbols.append(
                {
                    "question_id": q_id,
                    "name": name,
                    "kind": kind,
                    "signature": signature,
                    "decorators": decorators,
                    "method_names": method_names,
                    "docstring": docstring,
                }
            )

        state = {
            "file_path": file_path,
            "symbols": state_symbols,
        }

        batch_results = await self.client.evaluate_batch(
            state=state,
            questions=questions,
            fallbacks=fallbacks,
        )

        for q_id, dec_res in batch_results.items():
            raw_val = dec_res.value
            fb_val = fallbacks[q_id]
            try:
                role_val = ArchitecturalRole(raw_val)
            except ValueError:
                role_val = ArchitecturalRole(fb_val)

            results[q_id] = DecisionResult(
                accepted=dec_res.accepted,
                value=role_val,
                confidence=dec_res.confidence,
                source=dec_res.source,
                raw_answer=dec_res.raw_answer,
                fallback_reason=dec_res.fallback_reason,
            )

        return results
