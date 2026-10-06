from __future__ import annotations

import pytest

from app.architecture.c4_exporter import (
    C4ArchitectureExporter,
    C4ArchitectureModel,
)
from app.context_builder.project_context import (
    ContextDesignConstraint,
    ContextEntity,
    ProjectContext,
)
from app.context_builder.project_context import (
    ContextRelationship as CtxRel,
)


@pytest.fixture
def sample_project_context() -> ProjectContext:
    entities = [
        ContextEntity(
            id="f1",
            name="frontend/src/app/page.tsx",
            kind="file",
            path="frontend/src/app/page.tsx",
            language="TypeScript",
        ),
        ContextEntity(
            id="s1",
            name="HomePage",
            kind="symbol",
            path="frontend/src/app/page.tsx",
            signature="function HomePage()",
            line_start=1,
            line_end=50,
        ),
        ContextEntity(
            id="f2",
            name="backend/app/main.py",
            kind="file",
            path="backend/app/main.py",
            language="Python",
        ),
        ContextEntity(
            id="f3",
            name="backend/app/models/repository.py",
            kind="file",
            path="backend/app/models/repository.py",
            language="Python",
        ),
        ContextEntity(
            id="f4",
            name="packages/contracts/src/types.ts",
            kind="file",
            path="packages/contracts/src/types.ts",
            language="TypeScript",
        ),
    ]

    relationships = [
        CtxRel(
            source_name="page",
            source_path="frontend/src/app/page.tsx",
            target_name="types",
            target_path="packages/contracts/src/types.ts",
            type="imports",
            confidence=1.0,
            resolution_method="tree_sitter_ast",
        ),
        CtxRel(
            source_name="main",
            source_path="backend/app/main.py",
            target_name="repository",
            target_path="backend/app/models/repository.py",
            type="imports",
            confidence=1.0,
            resolution_method="tree_sitter_ast",
        ),
    ]

    constraints = [
        ContextDesignConstraint(
            id="c1",
            domain="security",
            constraint_text="Repository access MUST be read-only",
            source_doc_path="AGENTS.md",
            priority="MUST",
        )
    ]

    return ProjectContext(
        target_type="repository",
        target_id="repo-1",
        target_name="TestApp",
        summary="A test repository for C4 export",
        entities=entities,
        relationships=relationships,
        design_constraints=constraints,
    )


def test_c4_export_from_project_context(sample_project_context: ProjectContext):
    model = C4ArchitectureExporter.export_from_project_context(
        sample_project_context,
        repo_name="TestApp",
        repo_description="Test application description",
    )

    assert isinstance(model, C4ArchitectureModel)
    assert model.system_name == "TestApp"
    assert model.system_description == "Test application description"

    # Verify containers detected
    container_ids = {c.id for c in model.containers}
    assert "container_frontend" in container_ids
    assert "container_backend" in container_ids
    assert "container_contracts" in container_ids
    assert "container_db" in container_ids  # Detected due to models/repository.py

    # Verify components
    assert len(model.components) > 0
    comp_paths = {c.source_path for c in model.components}
    assert any("frontend" in p for p in comp_paths)
    assert any("backend" in p for p in comp_paths)

    # Verify persons & external systems
    assert any(p.id == "person_dev" for p in model.persons)
    assert any(s.id == "sys_github" for s in model.systems)

    # Verify relationships
    assert len(model.relationships) > 0

    # Verify constraints
    assert len(model.constraints) == 1
    assert model.constraints[0]["domain"] == "security"


def test_mermaid_c4_context_diagram(sample_project_context: ProjectContext):
    model = C4ArchitectureExporter.export_from_project_context(
        sample_project_context,
        repo_name="TestApp",
    )
    mmd = model.to_mermaid_context()

    assert "C4Context" in mmd
    assert "title System Context Diagram for TestApp" in mmd
    assert "Person(" in mmd
    assert "System(" in mmd
    assert "System_Ext(" in mmd
    assert "Rel(" in mmd
    # Ensure person connects to the system, not unknown container shapes
    assert "Rel(person_dev, testapp" in mmd
    assert "container_core" not in mmd


def test_mermaid_c4_container_diagram(sample_project_context: ProjectContext):
    model = C4ArchitectureExporter.export_from_project_context(
        sample_project_context,
        repo_name="TestApp",
    )
    mmd = model.to_mermaid_container()

    assert "C4Container" in mmd
    assert "title Container Diagram for TestApp" in mmd
    assert "Container(" in mmd or "ContainerDb(" in mmd
    assert "Rel(" in mmd


def test_mermaid_c4_component_diagram(sample_project_context: ProjectContext):
    model = C4ArchitectureExporter.export_from_project_context(
        sample_project_context,
        repo_name="TestApp",
    )
    mmd = model.to_mermaid_component("container_backend")

    assert "C4Component" in mmd
    assert "Component(" in mmd


def test_mermaid_flowchart_diagram(sample_project_context: ProjectContext):
    model = C4ArchitectureExporter.export_from_project_context(
        sample_project_context,
        repo_name="TestApp",
    )
    flow = model.to_mermaid_flowchart("TB")

    assert "flowchart TB" in flow
    assert "subgraph" in flow
    assert "-->" in flow


def test_markdown_document_export(sample_project_context: ProjectContext):
    model = C4ArchitectureExporter.export_from_project_context(
        sample_project_context,
        repo_name="TestApp",
    )
    doc = model.to_markdown_document()

    assert "# TestApp — Architectural Specification (C4 Model)" in doc
    assert "## 1. System Overview" in doc
    assert "## 2. Level 1: System Context Diagram" in doc
    assert "```mermaid" in doc
    assert "## 3. Level 2: Container Architecture" in doc
    assert "## 4. Level 3: Component Architecture" in doc
    assert "## 5. Architectural Dependency Graph" in doc
    assert "## 6. Component Relationship & Interface Directory" in doc
    assert "## 7. Governing Architectural Invariants & Constraints" in doc
    assert "Repository access MUST be read-only" in doc


def test_empty_context_handling():
    empty_ctx = ProjectContext(
        target_type="repository",
        target_id="empty-1",
        target_name="EmptyRepo",
        summary="Empty repository context",
    )
    model = C4ArchitectureExporter.export_from_project_context(empty_ctx, repo_name="EmptyRepo")

    assert model.system_name == "EmptyRepo"
    assert len(model.containers) >= 1
    assert "C4Context" in model.to_mermaid_context()
    assert "flowchart TB" in model.to_mermaid_flowchart()
    assert len(model.to_markdown_document()) > 100


def test_mermaid_flowchart_edge_label_sanitization():
    entities = [
        ContextEntity(
            id="f1",
            name="backend/app/reset.py",
            kind="file",
            path="backend/app/reset.py",
            language="Python",
        ),
        ContextEntity(
            id="f2",
            name="backend/tests/test_reset.py",
            kind="file",
            path="backend/tests/test_reset.py",
            language="Python",
        ),
    ]
    relationships = [
        CtxRel(
            source_name="reset",
            source_path="backend/app/reset.py",
            target_name="test_reset",
            target_path="backend/tests/test_reset.py",
            type="tested_by",
            confidence=1.0,
            resolution_method="pytest_ast",
        ),
    ]
    ctx = ProjectContext(
        target_type="repository",
        target_id="repo-2",
        target_name="TestApp",
        summary="Testing edge label sanitization",
        entities=entities,
        relationships=relationships,
    )
    model = C4ArchitectureExporter.export_from_project_context(ctx, repo_name="TestApp")
    flowchart = model.to_mermaid_flowchart("TB")

    # Verify no unquoted parentheses or raw arrows in edge labels
    assert "-->|" in flowchart
    assert "(" not in flowchart.split("-->|")[1].split("|")[0]
    assert ")" not in flowchart.split("-->|")[1].split("|")[0]
    assert "->" not in flowchart.split("-->|")[1].split("|")[0]
