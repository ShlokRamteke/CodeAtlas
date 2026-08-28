from __future__ import annotations

from app.context_builder.builder import CurrentSystemContextBuilder


def test_build_component_brief() -> None:
    builder = CurrentSystemContextBuilder()

    files = [
        {"id": "f1", "path": "src/services/PaymentService.ts", "language": "typescript"},
        {"id": "f2", "path": "src/services/PaymentService.test.ts", "language": "typescript"},
    ]
    symbols = [
        {"id": "s1", "file_id": "f1", "name": "PaymentService", "kind": "class", "line_start": 9, "line_end": 20, "signature": "class PaymentService"},
        {"id": "s2", "file_id": "f1", "name": "charge", "kind": "method", "line_start": 12, "line_end": 15, "signature": "charge()"},
    ]
    dependencies = [
        {"source_file_id": "f1", "target_path": "../models/User", "imported_symbol": "User", "kind": "relative"},
    ]
    relationships = [
        {"source_name": "CheckoutService", "source_path": "src/services/CheckoutService.ts", "target_name": "PaymentService", "target_path": "src/services/PaymentService.ts", "type": "imports"},
        {"source_name": "PaymentService", "source_path": "src/services/PaymentService.ts", "target_name": "PaymentService.test", "target_path": "src/services/PaymentService.test.ts", "type": "tested_by"},
    ]

    brief = builder.build_component_brief("src/services/PaymentService.ts", files, symbols, dependencies, relationships)

    assert brief.name == "src/services/PaymentService.ts"
    assert brief.symbol_count == 2
    assert len(brief.callers) == 1
    assert brief.callers[0]["caller"] == "CheckoutService"
    assert len(brief.tests) == 1
    assert "src/services/PaymentService.test.ts" in brief.tests
    assert "PaymentService" in brief.human_summary
    assert "PROJECT CONTEXT BRIEFING" in brief.llm_context

