from __future__ import annotations

import pytest

from app.architecture.c4_exporter import (
    C4ArchitectureExporter,
    C4ArchitectureModel,
)
from app.context_builder.project_context import (
    ContextDesignConstraint,
    ContextEntity,
    ContextEvidence,
    ContextRelationship,
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

    # 2. Components belong to container_frontend and exclude root configs
    comp_names = {c.name for c in model.components}
    assert "Next.Config" not in comp_names
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

    # 4. Mermaid component diagram connects person to primary app component
    comp_mmd = model.to_mermaid_component()
    assert "Container_Boundary" in comp_mmd
    assert "comp_app" in comp_mmd
    assert "Rel(person_dev, comp_app" in comp_mmd


def test_c4_component_diagram_with_alias_references():
    """Verify that alias imports (@/components, @/lib) generate connected edges in C4Component."""
    entities = [
        ContextEntity(
            id="f1", name="app/page.tsx", kind="file", path="app/page.tsx", language="TypeScript"
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
            id="f3", name="lib/utils.ts", kind="file", path="lib/utils.ts", language="TypeScript"
        ),
        ContextEntity(
            id="s3", name="cn", kind="symbol", path="lib/utils.ts", signature="export function cn()"
        ),
    ]

    relationships = [
        ContextRelationship(
            source_name="ConvertPage",
            source_path="app/page.tsx",
            target_name="Dropzone",
            target_path="@/components/dropzone",
            type="imports",
            confidence=1.0,
            resolution_method="ast_import_resolver",
        ),
        ContextRelationship(
            source_name="Dropzone",
            source_path="components/dropzone.tsx",
            target_name="cn",
            target_path="@/lib/utils",
            type="imports",
            confidence=1.0,
            resolution_method="ast_import_resolver",
        ),
    ]

    ctx = ProjectContext(
        target_type="repository",
        target_id="repo-convert-zone",
        target_name="convert-zone",
        summary="Convert-zone application",
        entities=entities,
        relationships=relationships,
    )

    model = C4ArchitectureExporter.export_from_project_context(ctx, repo_name="convert-zone")

    # Check component dependencies list updated
    comp_map = {c.id: c for c in model.components}
    assert "comp_app" in comp_map
    assert "comp_components" in comp_map
    assert "comp_lib" in comp_map
    assert "UI Components" in comp_map["comp_app"].dependencies
    assert "Utilities & Libraries" in comp_map["comp_components"].dependencies

    # Check Mermaid component diagram renders relationships between components
    comp_mmd = model.to_mermaid_component()
    assert "Rel(comp_app, comp_components" in comp_mmd
    assert "Rel(comp_components, comp_lib" in comp_mmd


def test_c4_pure_backend_express_repository():
    """Verify that a pure Express / Node.js backend repo generates only container_backend."""
    entities = [
        ContextEntity(
            id="f1",
            name="server/controllers/formController.js",
            kind="file",
            path="server/controllers/formController.js",
            language="JavaScript",
        ),
        ContextEntity(
            id="s1",
            name="submitForm",
            kind="symbol",
            path="server/controllers/formController.js",
            signature="exports.submitForm",
        ),
        ContextEntity(
            id="f2",
            name="server/models/Form.js",
            kind="file",
            path="server/models/Form.js",
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
            id="f4", name="package.json", kind="file", path="package.json", language="JSON"
        ),
    ]

    ctx = ProjectContext(
        target_type="repository",
        target_id="repo-express",
        target_name="forms-api",
        summary="Form processing API",
        entities=entities,
        relationships=[],
    )

    model = C4ArchitectureExporter.export_from_project_context(ctx, repo_name="forms-api")

    # Exactly ONE container_backend (+ DB container if models detected)
    container_ids = [c.id for c in model.containers]
    assert "container_backend" in container_ids
    assert "container_frontend" not in container_ids
    assert "container_core" not in container_ids

    backend_cont = next(c for c in model.containers if c.id == "container_backend")
    assert "Node.js" in backend_cont.technology or "JavaScript" in backend_cont.technology
    assert backend_cont.container_type == "api"

    # Components properly classified
    comp_names = {c.name for c in model.components}
    assert "Controllers" in comp_names
    assert "Data Models & Schemas" in comp_names
    assert "Middleware & Auth" in comp_names
    assert "Package" not in comp_names


def test_c4_fullstack_monorepo():
    """Verify that a monorepo with both frontend and backend directories creates both containers."""
    entities = [
        ContextEntity(
            id="f1",
            name="frontend/src/components/button.tsx",
            kind="file",
            path="frontend/src/components/button.tsx",
            language="TypeScript",
        ),
        ContextEntity(
            id="f2",
            name="backend/app/api/endpoints.py",
            kind="file",
            path="backend/app/api/endpoints.py",
            language="Python",
        ),
        ContextEntity(
            id="f3",
            name="backend/app/models/user.py",
            kind="file",
            path="backend/app/models/user.py",
            language="Python",
        ),
    ]

    ctx = ProjectContext(
        target_type="repository",
        target_id="repo-fullstack",
        target_name="fullstack-app",
        summary="Fullstack web application",
        entities=entities,
        relationships=[],
    )

    model = C4ArchitectureExporter.export_from_project_context(ctx, repo_name="fullstack-app")

    container_ids = {c.id for c in model.containers}
    assert "container_frontend" in container_ids
    assert "container_backend" in container_ids

    # Container relationships include frontend calling backend
    cont_mmd = model.to_mermaid_container()
    assert "Rel(container_frontend, container_backend" in cont_mmd


def test_c4_component_symbol_roles_aggregation():
    """Verify that symbol architectural roles are aggregated onto C4 components."""
    entities = [
        ContextEntity(
            id="f1",
            name="backend/app/api/users.py",
            kind="file",
            path="backend/app/api/users.py",
            language="Python",
        ),
        ContextEntity(
            id="s1",
            name="get_users",
            kind="symbol",
            path="backend/app/api/users.py",
            signature="def get_users():",
            architectural_role="controller",
        ),
        ContextEntity(
            id="s2",
            name="create_user",
            kind="symbol",
            path="backend/app/api/users.py",
            signature="def create_user():",
            architectural_role="controller",
        ),
        ContextEntity(
            id="f2",
            name="backend/app/repositories/user_repo.py",
            kind="file",
            path="backend/app/repositories/user_repo.py",
            language="Python",
        ),
        ContextEntity(
            id="s3",
            name="UserRepository",
            kind="symbol",
            path="backend/app/repositories/user_repo.py",
            signature="class UserRepository:",
            architectural_role="repository",
        ),
    ]

    ctx = ProjectContext(
        target_type="repository",
        target_id="repo-roles",
        target_name="role-test-repo",
        summary="Role test app",
        entities=entities,
        relationships=[],
    )

    model = C4ArchitectureExporter.export_from_project_context(ctx, repo_name="role-test-repo")

    # Find component handling users API
    api_comp = next((c for c in model.components if "api" in c.id or "user" in c.id), None)
    assert api_comp is not None
    assert "controller" in api_comp.symbol_roles
    assert api_comp.symbol_roles["controller"] == 2
    assert api_comp.dominant_role == "controller"

    # Find repo component
    repo_comp = next((c for c in model.components if "repo" in c.id), None)
    assert repo_comp is not None
    assert "repository" in repo_comp.symbol_roles
    assert repo_comp.symbol_roles["repository"] == 1
    assert repo_comp.dominant_role == "repository"


def test_monorepo_multi_container_classification():
    """Verify that multi-container monorepos dynamically classify worker, cli, web, and library containers."""
    entities = [
        ContextEntity(
            id="f1",
            name="apps/web/src/pages/index.tsx",
            kind="file",
            path="apps/web/src/pages/index.tsx",
            language="TypeScript",
        ),
        ContextEntity(
            id="f2",
            name="services/api/src/main.py",
            kind="file",
            path="services/api/src/main.py",
            language="Python",
        ),
        ContextEntity(
            id="f3",
            name="services/worker/tasks.py",
            kind="file",
            path="services/worker/tasks.py",
            language="Python",
        ),
        ContextEntity(
            id="f4",
            name="cmd/atlas-cli/main.go",
            kind="file",
            path="cmd/atlas-cli/main.go",
            language="Go",
        ),
        ContextEntity(
            id="f5",
            name="packages/contracts/src/types.ts",
            kind="file",
            path="packages/contracts/src/types.ts",
            language="TypeScript",
        ),
    ]

    ctx = ProjectContext(
        target_type="repository",
        target_id="repo-monorepo",
        target_name="EnterpriseMonorepo",
        summary="Multi-service distributed architecture",
        entities=entities,
        relationships=[],
    )

    model = C4ArchitectureExporter.export_from_project_context(ctx, repo_name="EnterpriseMonorepo")

    container_map = {c.id: c for c in model.containers}
    assert "container_web" in container_map
    assert "container_api" in container_map
    assert "container_worker" in container_map
    assert "container_atlas_cli" in container_map
    assert "container_contracts" in container_map

    # Check classifications
    assert container_map["container_web"].container_type == "web_app"
    assert container_map["container_api"].container_type == "api"
    assert container_map["container_worker"].container_type == "worker"
    assert container_map["container_atlas_cli"].container_type == "cli_tool"
    assert container_map["container_contracts"].container_type == "shared_library"

    # Technologies
    assert "Go" in container_map["container_atlas_cli"].technology
    assert (
        "Worker" in container_map["container_worker"].technology
        or "Python" in container_map["container_worker"].technology
    )

    # Mermaid diagram contains ContainerQueue for worker
    mmd = model.to_mermaid_container()
    assert "ContainerQueue(container_worker" in mmd
    assert "Container(container_atlas_cli" in mmd


@pytest.mark.asyncio
async def test_export_from_project_context_async_systemone():
    """Verify async C4 export leverages System One batch classification with MockSystemOneClient."""
    from app.semantic.client import MockSystemOneClient
    from app.semantic.container_classifier import ContainerClassifier

    mock_client = MockSystemOneClient(enabled=True)
    # Configure mock responses for batch container classifications
    mock_client.set_choice_response("cont_0", "worker", confidence=0.96)
    mock_client.set_choice_response("cont_1", "api", confidence=0.92)

    classifier = ContainerClassifier(client=mock_client)

    entities = [
        ContextEntity(
            id="f1",
            name="services/job-runner/worker.py",
            kind="file",
            path="services/job-runner/worker.py",
            language="Python",
        ),
        ContextEntity(
            id="f2",
            name="services/billing-api/server.py",
            kind="file",
            path="services/billing-api/server.py",
            language="Python",
        ),
    ]

    ctx = ProjectContext(
        target_type="repository",
        target_id="repo-async",
        target_name="AsyncRepo",
        summary="Async service test",
        entities=entities,
        relationships=[],
    )

    model = await C4ArchitectureExporter.export_from_project_context_async(
        context=ctx,
        repo_name="AsyncRepo",
        container_classifier=classifier,
    )

    container_map = {c.id: c for c in model.containers}
    assert "container_job_runner" in container_map
    assert "container_billing_api" in container_map

    assert container_map["container_job_runner"].container_type == "worker"
    assert container_map["container_billing_api"].container_type == "api"


def test_c4_export_mongodb_detection_via_mongoose():
    """Verify MongoDB is verified as the database technology and correctly described

    in C4 containers, Mermaid C4 container diagram, and flowchart when mongoose is imported.
    """
    entities = [
        ContextEntity(
            id="f1",
            name="src/models/user.ts",
            kind="file",
            path="src/models/user.ts",
            language="TypeScript",
        ),
        ContextEntity(
            id="f2",
            name="src/routes/users.ts",
            kind="file",
            path="src/routes/users.ts",
            language="TypeScript",
        ),
        ContextEntity(
            id="f3",
            name="src/server.ts",
            kind="file",
            path="src/server.ts",
            language="TypeScript",
        ),
        ContextEntity(
            id="s1",
            name="UserSchema",
            kind="symbol",
            path="src/models/user.ts",
            signature="const UserSchema = new mongoose.Schema({ name: String, email: String });",
            architectural_role="data_model",
        ),
    ]

    relationships = [
        ContextRelationship(
            source_name="user",
            source_path="src/models/user.ts",
            target_name="mongoose",
            target_path="mongoose",
            type="imports",
            confidence=1.0,
            resolution_method="tree_sitter_ast",
        ),
        ContextRelationship(
            source_name="server",
            source_path="src/server.ts",
            target_name="users",
            target_path="src/routes/users.ts",
            type="imports",
            confidence=1.0,
            resolution_method="tree_sitter_ast",
        ),
    ]

    evidence = [
        ContextEvidence(
            id="ev1",
            source_path="src/models/user.ts",
            kind="import_statement",
            content="import mongoose, { Schema } from 'mongoose';",
            confidence=1.0,
            provenance="tree_sitter_ast",
        ),
        ContextEvidence(
            id="ev2",
            source_path="src/server.ts",
            kind="import_statement",
            content="mongoose.connect(process.env.MONGODB_URI);",
            confidence=1.0,
            provenance="tree_sitter_ast",
        ),
    ]

    ctx = ProjectContext(
        target_type="repository",
        target_id="repo-mongo-test",
        target_name="ECommerceAPI",
        summary="API with MongoDB backend",
        entities=entities,
        relationships=relationships,
        evidence=evidence,
    )

    model = C4ArchitectureExporter.export_from_project_context(
        ctx,
        repo_name="ECommerceAPI",
        repo_description="E-commerce backend with MongoDB database",
    )

    container_map = {c.id: c for c in model.containers}
    assert "container_db" in container_map
    db_container = container_map["container_db"]

    # Verify database technology and description are verified as MongoDB
    assert db_container.technology == "MongoDB"
    assert db_container.name == "Application Database"
    assert "Document database storing application collections and state (MongoDB)" in db_container.description
    assert db_container.container_type == "database"

    # Verify Mermaid C4 Container Diagram renders ContainerDb with MongoDB
    mermaid_cont = model.to_mermaid_container()
    assert 'ContainerDb(container_db, "Application Database", "MongoDB"' in mermaid_cont

    # Verify Mermaid Flowchart renders subgraph with MongoDB
    flowchart = model.to_mermaid_flowchart("TB")
    assert 'subgraph container_db["Application Database (MongoDB)"]' in flowchart

    # Verify backend queries container_db relationship
    db_rel = next((r for r in model.relationships if r.target_id == "container_db"), None)
    assert db_rel is not None
    assert db_rel.technology == "MongoDB"
    assert "queries" in db_rel.relationship_type.lower()


def test_c4_export_mongodb_detection_via_pymongo():
    """Verify MongoDB detection for Python repositories importing pymongo or motor."""
    entities = [
        ContextEntity(
            id="f1",
            name="app/database.py",
            kind="file",
            path="app/database.py",
            language="Python",
        ),
        ContextEntity(
            id="f2",
            name="app/main.py",
            kind="file",
            path="app/main.py",
            language="Python",
        ),
        ContextEntity(
            id="s1",
            name="get_mongo_client",
            kind="symbol",
            path="app/database.py",
            signature="def get_mongo_client() -> MongoClient:",
            architectural_role="storage",
        ),
    ]

    relationships = [
        ContextRelationship(
            source_name="database",
            source_path="app/database.py",
            target_name="pymongo",
            target_path="pymongo",
            type="imports",
        )
    ]

    evidence = [
        ContextEvidence(
            id="ev1",
            source_path="app/database.py",
            kind="import_statement",
            content="from pymongo import MongoClient",
        )
    ]

    ctx = ProjectContext(
        target_type="repository",
        target_id="repo-pymongo",
        target_name="PythonMongoApp",
        summary="Python app with PyMongo",
        entities=entities,
        relationships=relationships,
        evidence=evidence,
    )

    model = C4ArchitectureExporter.export_from_project_context(ctx, repo_name="PythonMongoApp")
    db_cont = next((c for c in model.containers if c.id == "container_db"), None)
    assert db_cont is not None
    assert db_cont.technology == "MongoDB"
    assert "MongoDB" in db_cont.description


def test_c4_export_postgresql_and_sqlite_detection():
    """Verify PostgreSQL and SQLite databases are accurately detected from driver imports."""
    # Test PostgreSQL
    pg_ctx = ProjectContext(
        target_type="repository",
        target_id="repo-pg",
        target_name="PostgresApp",
        summary="Postgres app",
        entities=[
            ContextEntity(id="f1", name="src/db.ts", kind="file", path="src/db.ts", language="TypeScript"),
            ContextEntity(id="f2", name="src/server.ts", kind="file", path="src/server.ts", language="TypeScript"),
        ],
        relationships=[
            ContextRelationship(source_name="db", source_path="src/db.ts", target_name="pg", target_path="pg", type="imports"),
        ],
        evidence=[
            ContextEvidence(id="e1", source_path="src/db.ts", kind="import_statement", content="import { Pool } from 'pg';"),
        ],
    )
    pg_model = C4ArchitectureExporter.export_from_project_context(pg_ctx, repo_name="PostgresApp")
    pg_db = next((c for c in pg_model.containers if c.id == "container_db"), None)
    assert pg_db is not None
    assert pg_db.technology == "PostgreSQL"

    # Test SQLite
    sqlite_ctx = ProjectContext(
        target_type="repository",
        target_id="repo-sqlite",
        target_name="SQLiteApp",
        summary="SQLite app",
        entities=[
            ContextEntity(id="f1", name="src/data.db", kind="file", path="src/data.db", language="Binary"),
            ContextEntity(id="f2", name="src/app.py", kind="file", path="src/app.py", language="Python"),
        ],
        relationships=[
            ContextRelationship(source_name="app", source_path="src/app.py", target_name="sqlite3", target_path="sqlite3", type="imports"),
        ],
        evidence=[
            ContextEvidence(id="e1", source_path="src/app.py", kind="import_statement", content="import sqlite3"),
        ],
    )
    sqlite_model = C4ArchitectureExporter.export_from_project_context(sqlite_ctx, repo_name="SQLiteApp")
    sqlite_db = next((c for c in sqlite_model.containers if c.id == "container_db"), None)
    assert sqlite_db is not None
    assert sqlite_db.technology == "SQLite"

