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


def test_c4_dynamic_javascript_repository_detection():
    """Verify that a JavaScript repository dynamically detects Node.js / JavaScript, not FastAPI."""
    entities = [
        ContextEntity(
            id="f1",
            name="server/clearLegacyData.js",
            kind="file",
            path="server/clearLegacyData.js",
            language="JavaScript",
        ),
        ContextEntity(
            id="f2",
            name="server/controllers/formController.js",
            kind="file",
            path="server/controllers/formController.js",
            language="JavaScript",
        ),
        ContextEntity(
            id="f3",
            name="server/middleware/adminAuth.js",
            kind="file",
            path="server/middleware/adminAuth.js",
            language="JavaScript",
        ),
        ContextEntity(
            id="f4",
            name="server/models/Conversation.js",
            kind="file",
            path="server/models/Conversation.js",
            language="JavaScript",
        ),
    ]

    ctx = ProjectContext(
        target_type="repository",
        target_id="repo-js",
        target_name="JSServerApp",
        summary="A pure JavaScript Node.js application",
        entities=entities,
        relationships=[],
    )

    model = C4ArchitectureExporter.export_from_project_context(ctx, repo_name="JSServerApp")

    # Find backend container
    backend_cont = next((c for c in model.containers if c.id == "container_backend"), None)
    assert backend_cont is not None
    assert backend_cont.technology == "Node.js / JavaScript"
    assert "Python" not in backend_cont.technology
    assert "FastAPI" not in backend_cont.technology
    assert "AST parsing" not in backend_cont.description

    # Find component technologies
    for comp in model.components:
        assert comp.technology == "JavaScript"
        assert comp.technology != "Python"


def test_c4_filters_non_code_files_and_config():
    """Verify that root documentation, config, and lock files are not treated as C4 components or containers."""
    entities = [
        ContextEntity(
            id="f1",
            name="README.md",
            kind="file",
            path="README.md",
            language="Markdown",
        ),
        ContextEntity(
            id="f2",
            name="skills-lock.json",
            kind="file",
            path="skills-lock.json",
            language="JSON",
        ),
        ContextEntity(
            id="f3",
            name="vercel.json",
            kind="file",
            path="vercel.json",
            language="JSON",
        ),
        ContextEntity(
            id="f4",
            name="server/controllers/formController.js",
            kind="file",
            path="server/controllers/formController.js",
            language="JavaScript",
        ),
        ContextEntity(
            id="f5",
            name="server/models/Form.js",
            kind="file",
            path="server/models/Form.js",
            language="JavaScript",
        ),
    ]

    ctx = ProjectContext(
        target_type="repository",
        target_id="repo-filtered",
        target_name="MyWebApp",
        summary="Web app with root configs and server code",
        entities=entities,
        relationships=[],
    )

    model = C4ArchitectureExporter.export_from_project_context(ctx, repo_name="MyWebApp")

    # 1. Non-code files must not be components
    component_names = {c.name.lower() for c in model.components}
    assert "readme" not in component_names
    assert "skills-lock" not in component_names
    assert "vercel" not in component_names

    # 2. No bogus "container_core" created solely for root configs
    container_ids = {c.id for c in model.containers}
    assert "container_core" not in container_ids
    assert "container_backend" in container_ids

    # 3. No container has "Json / REST API" technology
    for cont in model.containers:
        assert "Json" not in cont.technology
        assert "json" not in cont.technology.lower()


def test_c4_pure_frontend_nextjs_repository_detection():
    """Verify that a Next.js App Router repository with app/, components/, hooks/, lib/
    creates exactly ONE frontend container and NO phantom backend or per-folder services."""
    entities = [
        ContextEntity(
            id="f1",
            name="app/page.tsx",
            kind="file",
            path="app/page.tsx",
            language="TypeScript",
        ),
        ContextEntity(
            id="s1",
            name="ConvertPage",
            kind="symbol",
            path="app/page.tsx",
            signature="export default function ConvertPage()",
        ),
        ContextEntity(
            id="f2",
            name="components/dropzone.tsx",
            kind="file",
            path="components/dropzone.tsx",
            language="TypeScript",
        ),
        ContextEntity(
            id="s2",
            name="Dropzone",
            kind="symbol",
            path="components/dropzone.tsx",
            signature="export function Dropzone()",
        ),
        ContextEntity(
            id="f3",
            name="hooks/use-convert.ts",
            kind="file",
            path="hooks/use-convert.ts",
            language="TypeScript",
        ),
        ContextEntity(
            id="f4",
            name="lib/utils.ts",
            kind="file",
            path="lib/utils.ts",
            language="TypeScript",
        ),
        ContextEntity(
            id="f5",
            name="next.config.js",
            kind="file",
            path="next.config.js",
            language="JavaScript",
        ),
    ]

    ctx = ProjectContext(
        target_type="repository",
        target_id="repo-convert-zone",
        target_name="convert-zone",
        summary="Online file converter built with Next.js",
        entities=entities,
        relationships=[],
    )

    model = C4ArchitectureExporter.export_from_project_context(ctx, repo_name="convert-zone")

    # 1. Exactly ONE container: container_frontend
    container_ids = [c.id for c in model.containers]
    assert container_ids == ["container_frontend"]
    assert "container_backend" not in container_ids
    assert "container_components" not in container_ids
    assert "container_hooks" not in container_ids
    assert "container_lib" not in container_ids
    assert "container_core" not in container_ids

    frontend_cont = model.containers[0]
    assert frontend_cont.container_type == "web_app"
    assert "Next.js" in frontend_cont.technology
    assert "TypeScript" in frontend_cont.technology
    assert "Backend API" not in frontend_cont.description

    # 2. Components belong to container_frontend
    assert len(model.components) >= 3
    for comp in model.components:
        assert comp.container_id == "container_frontend"

    # 3. Mermaid container diagram has NO phantom backend or GitHub calls
    mmd = model.to_mermaid_container()
    assert "container_backend" not in mmd
    assert "Components Service" not in mmd
    assert "Hooks Service" not in mmd
    assert "Lib Service" not in mmd
    assert "Pulls Git history and issues" not in mmd
    assert "Rel(person_dev, container_frontend" in mmd

