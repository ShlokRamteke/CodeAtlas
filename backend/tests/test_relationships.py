from __future__ import annotations

from app.parser.ast_parser import ExtractedDependency, ExtractedSymbol, ParsedFileResult
from app.parser.relationship_analyzer import RelationshipAnalyzer


def test_test_file_matching() -> None:
    all_files = [
        "src/services/PaymentService.ts",
        "src/services/UserService.ts",
        "src/services/__tests__/PaymentService.test.ts",
        "backend/app/auth.py",
        "backend/tests/test_auth.py",
    ]

    target1 = RelationshipAnalyzer.find_target_for_test(
        "src/services/__tests__/PaymentService.test.ts", all_files
    )
    assert target1 == "src/services/PaymentService.ts"

    target2 = RelationshipAnalyzer.find_target_for_test("backend/tests/test_auth.py", all_files)
    assert target2 == "backend/app/auth.py"


def test_architecture_graph_generation() -> None:
    analyzer = RelationshipAnalyzer()

    files = [
        ParsedFileResult(
            path="src/services/PaymentService.ts",
            language="typescript",
            symbols=[
                ExtractedSymbol(name="PaymentService", kind="class", line_start=1, line_end=20),
                ExtractedSymbol(name="charge", kind="method", line_start=5, line_end=15),
            ],
            dependencies=[
                ExtractedDependency(
                    target_path="./database", imported_symbol="db", kind="relative"
                ),
                ExtractedDependency(
                    target_path="stripe", imported_symbol="Stripe", kind="external"
                ),
            ],
        ),
        ParsedFileResult(
            path="src/services/PaymentService.test.ts",
            language="typescript",
            symbols=[
                ExtractedSymbol(name="testCharge", kind="function", line_start=1, line_end=10),
            ],
            dependencies=[
                ExtractedDependency(
                    target_path="./PaymentService",
                    imported_symbol="PaymentService",
                    kind="relative",
                ),
            ],
        ),
    ]

    graph = analyzer.analyze_repository(files)
    assert graph.file_count == 2
    assert graph.symbol_count == 3
    assert graph.dependency_count == 3
    assert graph.languages["typescript"] == 2

    # Check component grouping
    assert len(graph.major_components) >= 1
    comp = graph.major_components[0]
    assert comp.path == "src/services"
    assert comp.tested_by == "src/services/PaymentService.test.ts"

    # Check relationships
    rel_types = {r.type for r in graph.relationships}
    assert "tested_by" in rel_types
    assert "imports" in rel_types


def test_resolve_import_path_aliases_and_relatives() -> None:
    all_files = [
        "app/page.tsx",
        "components/dropzone.tsx",
        "components/ui/button.tsx",
        "hooks/use-convert.ts",
        "lib/utils.ts",
        "backend/app/models/user.py",
        "backend/app/api/endpoints.py",
    ]

    # Alias @/ resolution
    res1 = RelationshipAnalyzer.resolve_import_path(
        "app/page.tsx", "@/components/dropzone", all_files
    )
    assert res1 == "components/dropzone.tsx"

    res2 = RelationshipAnalyzer.resolve_import_path(
        "components/dropzone.tsx", "@/lib/utils", all_files
    )
    assert res2 == "lib/utils.ts"

    # Relative ../ resolution
    res3 = RelationshipAnalyzer.resolve_import_path(
        "components/dropzone.tsx", "./ui/button", all_files
    )
    assert res3 == "components/ui/button.tsx"

    # Python module notation
    res4 = RelationshipAnalyzer.resolve_import_path(
        "backend/app/api/endpoints.py", "app.models.user", all_files
    )
    assert res4 == "backend/app/models/user.py"

    # Unresolved fallback
    res5 = RelationshipAnalyzer.resolve_import_path("app/page.tsx", "@/external/library", all_files)
    assert res5 == "external/library"
