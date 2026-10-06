from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.context_builder.project_context import ProjectContext
from app.parser.relationship_analyzer import ArchitectureGraph


def _sanitize_id(val: str) -> str:
    """Sanitize string into a safe identifier for Mermaid nodes."""
    sanitized = re.sub(r"[^a-zA-Z0-9_]", "_", val)
    if sanitized and sanitized[0].isdigit():
        sanitized = "n_" + sanitized
    return sanitized or "node"


@dataclass
class C4Person:
    id: str
    name: str
    description: str
    external: bool = False


@dataclass
class C4System:
    id: str
    name: str
    description: str
    external: bool = False


@dataclass
class C4Component:
    id: str
    name: str
    container_id: str
    technology: str
    description: str
    source_path: str
    symbol_count: int = 0
    file_count: int = 0
    dependencies: List[str] = field(default_factory=list)


@dataclass
class C4Container:
    id: str
    name: str
    technology: str
    description: str
    container_type: str  # web_app, api, database, worker, library
    path: Optional[str] = None
    components: List[C4Component] = field(default_factory=list)


@dataclass
class C4Relationship:
    source_id: str
    target_id: str
    description: str
    technology: Optional[str] = None
    relationship_type: str = "uses"  # uses, imports, calls, queries, tested_by


@dataclass
class C4ArchitectureModel:
    system_name: str
    system_description: str
    persons: List[C4Person] = field(default_factory=list)
    systems: List[C4System] = field(default_factory=list)
    containers: List[C4Container] = field(default_factory=list)
    components: List[C4Component] = field(default_factory=list)
    relationships: List[C4Relationship] = field(default_factory=list)
    constraints: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def to_mermaid_context(self) -> str:
        """Generate Mermaid C4Context diagram definition."""
        lines = [
            "C4Context",
            f"  title System Context Diagram for {self.system_name}",
        ]
        # Persons
        for p in self.persons:
            tag = "Person_Ext" if p.external else "Person"
            sid = _sanitize_id(p.id)
            lines.append(f'  {tag}({sid}, "{p.name}", "{p.description}")')

        # Main system
        main_sys_id = _sanitize_id(self.system_name.lower())
        lines.append(f'  Enterprise_Boundary(b0, "{self.system_name} Boundary") {{')
        lines.append(
            f'    System({main_sys_id}, "{self.system_name}", "{self.system_description}")'
        )
        lines.append("  }")

        # External systems
        for s in self.systems:
            if s.id != main_sys_id and s.name != self.system_name:
                sid = _sanitize_id(s.id)
                tag = "System_Ext" if s.external else "System"
                lines.append(f'  {tag}({sid}, "{s.name}", "{s.description}")')

        # Context relationships
        seen_edges = set()
        for r in self.relationships:
            # Only render edges involving persons or external systems or the main system
            src = _sanitize_id(r.source_id)
            tgt = _sanitize_id(r.target_id)
            # Normalize to container or system level
            edge_key = (src, tgt)
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                tech = f', "{r.technology}"' if r.technology else ""
                lines.append(f'  Rel({src}, {tgt}, "{r.description}"{tech})')

        return "\n".join(lines)

    def to_mermaid_container(self) -> str:
        """Generate Mermaid C4Container diagram definition."""
        lines = [
            "C4Container",
            f"  title Container Diagram for {self.system_name}",
        ]
        for p in self.persons:
            tag = "Person_Ext" if p.external else "Person"
            sid = _sanitize_id(p.id)
            lines.append(f'  {tag}({sid}, "{p.name}", "{p.description}")')

        lines.append(f'  Container_Boundary(b_containers, "{self.system_name}") {{')
        for c in self.containers:
            cid = _sanitize_id(c.id)
            if c.container_type == "database":
                tag = "ContainerDb"
            elif c.container_type == "worker":
                tag = "ContainerQueue"
            else:
                tag = "Container"
            lines.append(f'    {tag}({cid}, "{c.name}", "{c.technology}", "{c.description}")')
        lines.append("  }")

        for s in self.systems:
            if s.external:
                sid = _sanitize_id(s.id)
                lines.append(f'  System_Ext({sid}, "{s.name}", "{s.description}")')

        # Container-level relationships
        container_ids = {c.id for c in self.containers}
        external_ids = {s.id for s in self.systems} | {p.id for p in self.persons}
        rendered_rels = set()

        for r in self.relationships:
            src = r.source_id
            tgt = r.target_id
            # Resolve component to container if needed
            src_c = next((comp.container_id for comp in self.components if comp.id == src), src)
            tgt_c = next((comp.container_id for comp in self.components if comp.id == tgt), tgt)

            if (
                src_c != tgt_c
                and (src_c in container_ids or src_c in external_ids)
                and (tgt_c in container_ids or tgt_c in external_ids)
            ):
                edge_key = (src_c, tgt_c)
                if edge_key not in rendered_rels:
                    rendered_rels.add(edge_key)
                    s_id = _sanitize_id(src_c)
                    t_id = _sanitize_id(tgt_c)
                    tech = f', "{r.technology}"' if r.technology else ""
                    lines.append(f'  Rel({s_id}, {t_id}, "{r.description}"{tech})')

        return "\n".join(lines)

    def to_mermaid_component(self, container_id: Optional[str] = None) -> str:
        """Generate Mermaid C4Component diagram for a specific or primary container."""
        # Find target container
        target_container = None
        if container_id:
            target_container = next((c for c in self.containers if c.id == container_id), None)
        if not target_container:
            # Pick first container with components
            target_container = next(
                (c for c in self.containers if c.components),
                self.containers[0] if self.containers else None,
            )

        if not target_container:
            return "C4Component\n  title No Components Available"

        lines = [
            "C4Component",
            f"  title Component Diagram for {target_container.name}",
            f'  Container_Boundary(b_comp_{_sanitize_id(target_container.id)}, "{target_container.name}") {{',
        ]

        target_comp_ids = set()
        for comp in target_container.components:
            cid = _sanitize_id(comp.id)
            target_comp_ids.add(comp.id)
            desc = (
                f"{comp.file_count} files, {comp.symbol_count} symbols. {comp.description}".strip()
            )
            lines.append(f'    Component({cid}, "{comp.name}", "{comp.technology}", "{desc}")')
        lines.append("  }")

        # Neighboring containers / external systems connected to these components
        external_connected = set()
        for r in self.relationships:
            if r.source_id in target_comp_ids and r.target_id not in target_comp_ids:
                external_connected.add(r.target_id)
            elif r.target_id in target_comp_ids and r.source_id not in target_comp_ids:
                external_connected.add(r.source_id)

        for ext_id in external_connected:
            cont = next((c for c in self.containers if c.id == ext_id), None)
            if cont:
                lines.append(
                    f'  Container({_sanitize_id(cont.id)}, "{cont.name}", "{cont.technology}", "{cont.description}")'
                )
            else:
                sys = next((s for s in self.systems if s.id == ext_id), None)
                if sys:
                    lines.append(
                        f'  System_Ext({_sanitize_id(sys.id)}, "{sys.name}", "{sys.description}")'
                    )

        # Relationships
        rendered_rels = set()
        for r in self.relationships:
            if r.source_id in target_comp_ids or r.target_id in target_comp_ids:
                edge_key = (r.source_id, r.target_id)
                if edge_key not in rendered_rels:
                    rendered_rels.add(edge_key)
                    s_id = _sanitize_id(r.source_id)
                    t_id = _sanitize_id(r.target_id)
                    tech = f', "{r.technology}"' if r.technology else ""
                    lines.append(f'  Rel({s_id}, {t_id}, "{r.description}"{tech})')

        return "\n".join(lines)

    def to_mermaid_flowchart(self, direction: str = "TB") -> str:
        """
        Generate portable standard Mermaid flowchart (widely supported by GFM and GitHub).
        Organizes components into container subgraphs and draws verified dependencies.
        """
        lines = [
            f"flowchart {direction}",
        ]

        # Draw containers as subgraphs
        all_comp_ids = set()
        for c in self.containers:
            cid = _sanitize_id(c.id)
            lines.append(f'    subgraph {cid}["{c.name} ({c.technology})"]')
            if c.components:
                for comp in c.components:
                    comp_id = _sanitize_id(comp.id)
                    all_comp_ids.add(comp.id)
                    badge = f"<br/><small>{comp.file_count} files &bull; {comp.symbol_count} syms</small>"
                    lines.append(f'        {comp_id}["{comp.name}{badge}"]')
            else:
                # Leaf container without subcomponents (e.g. database)
                lines.append(f'        node_{cid}["{c.name}"]')
            lines.append("    end")

        # External systems
        for s in self.systems:
            if s.external:
                sid = _sanitize_id(s.id)
                lines.append(f'    {sid}[("{s.name}<br/><small>External</small>")]:::externalSys')

        # Styles
        lines.append(
            "    classDef externalSys fill:#334155,stroke:#64748b,stroke-width:1px,color:#f8fafc;"
        )

        # Draw relationships
        rendered_edges = set()
        for r in self.relationships:
            src = _sanitize_id(r.source_id)
            tgt = _sanitize_id(r.target_id)
            if src == tgt:
                continue

            edge_key = (src, tgt)
            if edge_key not in rendered_edges:
                rendered_edges.add(edge_key)
                label = (
                    f"|{r.description}|"
                    if r.description and r.description not in ["uses", "imports"]
                    else ""
                )
                lines.append(f"    {src} -->{label} {tgt}")

        return "\n".join(lines)

    def to_markdown_document(self) -> str:
        """
        Generate a comprehensive, portable GFM architectural specification ready
        to be saved into ARCHITECTURE.md or documentation repositories.
        """
        doc = [
            f"# {self.system_name} — Architectural Specification (C4 Model)",
            "",
            "> Automated Architectural Export generated by CodeAtlas Pre-Change Investigation Engine.",
            "",
            "## 1. System Overview",
            "",
            f"**System:** {self.system_name}",
            f"**Description:** {self.system_description}",
            "",
            "### Actors & Stakeholders",
            "| Actor | Type | Description |",
            "| :--- | :--- | :--- |",
        ]

        for p in self.persons:
            doc.append(
                f"| **{p.name}** | {'External' if p.external else 'Internal'} | {p.description} |"
            )

        doc.extend(
            [
                "",
                "## 2. Level 1: System Context Diagram",
                "",
                "The System Context diagram details how users and external systems interact with the core solution.",
                "",
                "```mermaid",
                self.to_mermaid_context(),
                "```",
                "",
                "## 3. Level 2: Container Architecture",
                "",
                "The Container diagram outlines high-level deployable units, runtimes, and databases.",
                "",
                "```mermaid",
                self.to_mermaid_container(),
                "```",
                "",
                "### Container Catalog",
                "| Container | Type | Technology | Description | Components |",
                "| :--- | :--- | :--- | :--- | :--- |",
            ]
        )

        for c in self.containers:
            doc.append(
                f"| **{c.name}** | `{c.container_type}` | {c.technology} | {c.description} | {len(c.components)} components |"
            )

        doc.extend(
            [
                "",
                "## 4. Level 3: Component Architecture",
                "",
                "Detailed breakdown of internal modular components, responsibilities, and structural bounds.",
                "",
            ]
        )

        for c in self.containers:
            if c.components:
                doc.extend(
                    [
                        f"### Component Diagram: {c.name}",
                        "",
                        "```mermaid",
                        self.to_mermaid_component(c.id),
                        "```",
                        "",
                        "#### Components in " + c.name,
                        "| Component | Technology | Path | Files | Symbols | Key Dependencies |",
                        "| :--- | :--- | :--- | :--- | :--- | :--- |",
                    ]
                )
                for comp in c.components:
                    deps_str = ", ".join(f"`{d}`" for d in comp.dependencies[:4]) or "*None*"
                    if len(comp.dependencies) > 4:
                        deps_str += f" (+{len(comp.dependencies) - 4} more)"
                    doc.append(
                        f"| **{comp.name}** | {comp.technology} | `{comp.source_path}` | {comp.file_count} | {comp.symbol_count} | {deps_str} |"
                    )
                doc.append("")

        doc.extend(
            [
                "## 5. Architectural Dependency Graph",
                "",
                "Standard Mermaid dependency flowchart illustrating verified inter-component and cross-container links:",
                "",
                "```mermaid",
                self.to_mermaid_flowchart("TB"),
                "```",
                "",
                "## 6. Component Relationship & Interface Directory",
                "",
                "| Source | Target | Relationship | Technology / Protocol |",
                "| :--- | :--- | :--- | :--- |",
            ]
        )

        for r in self.relationships:
            tech = r.technology or "Internal"
            doc.append(f"| `{r.source_id}` | `{r.target_id}` | {r.description} | {tech} |")

        if self.constraints:
            doc.extend(
                [
                    "",
                    "## 7. Governing Architectural Invariants & Constraints",
                    "",
                    "| Domain | Priority | Constraint Statement | Source Document |",
                    "| :--- | :--- | :--- | :--- |",
                ]
            )
            for const in self.constraints:
                domain = const.get("domain", "General")
                prio = const.get("priority", "MUST")
                text = const.get("constraint_text", const.get("statement", ""))
                src = const.get("source_doc_path", "")
                doc.append(f"| **{domain}** | `{prio}` | {text} | `{src}` |")

        doc.append("")
        return "\n".join(doc)


class C4ArchitectureExporter:
    """
    Exports clean C4 Container/Component models, Mermaid diagrams, and
    portable architecture specifications from canonical ProjectContext.
    """

    @classmethod
    def export_from_project_context(
        cls,
        context: ProjectContext,
        repo_name: str = "Repository",
        repo_description: Optional[str] = None,
    ) -> C4ArchitectureModel:
        """
        Synthesize C4 model from canonical ProjectContext.
        """
        description = repo_description or context.summary or f"Architecture model for {repo_name}"

        # 1. Identify containers
        containers_map: Dict[str, C4Container] = {}
        components_map: Dict[str, C4Component] = {}
        all_entities = context.entities

        # File and symbol entities
        files = [e for e in all_entities if e.kind == "file"]
        symbols = [e for e in all_entities if e.kind == "symbol"]

        # Count symbols by file path
        sym_count_by_file: Dict[str, int] = {}
        for s in symbols:
            sym_count_by_file[s.path] = sym_count_by_file.get(s.path, 0) + 1

        # Classify files into containers & components
        for f in files:
            p = Path(f.path)
            parts = p.parts

            # Container detection heuristic
            top_dir = parts[0].lower() if parts else "root"
            if top_dir in ["frontend", "web", "client", "ui"]:
                cont_id = "container_frontend"
                cont_name = "Frontend Web Application"
                cont_tech = "Next.js / TypeScript / React"
                cont_type = "web_app"
                cont_desc = "Single-page responsive user interface and visualization dashboard"
            elif top_dir in ["backend", "server", "api", "app"]:
                cont_id = "container_backend"
                cont_name = "Backend API & Services"
                cont_tech = "FastAPI / Python 3.11"
                cont_type = "api"
                cont_desc = (
                    "Core REST API, AST parsing, historical intelligence, and investigation engine"
                )
            elif top_dir in ["packages", "contracts", "shared"]:
                cont_id = "container_contracts"
                cont_name = "Shared Contracts & Schemas"
                cont_tech = "TypeScript / Type Definitions"
                cont_type = "library"
                cont_desc = "Shared API contracts and typed data models"
            else:
                cont_id = "container_core"
                cont_name = "Core Application"
                cont_tech = f.language or "Multi-language"
                cont_type = "api"
                cont_desc = "Core repository application code"

            if cont_id not in containers_map:
                containers_map[cont_id] = C4Container(
                    id=cont_id,
                    name=cont_name,
                    technology=cont_tech,
                    description=cont_desc,
                    container_type=cont_type,
                    path=top_dir,
                )

            # Component detection heuristic
            # Group by 2 directory levels (e.g. backend/app/investigation or frontend/src/components)
            if len(parts) >= 3:
                comp_path = "/".join(parts[:3])
                comp_name = " / ".join(parts[1:3]).title()
            elif len(parts) == 2:
                comp_path = "/".join(parts[:2])
                comp_name = parts[1].title()
            else:
                comp_path = f.path
                comp_name = p.stem.title()

            comp_id = f"comp_{_sanitize_id(comp_path)}"
            if comp_id not in components_map:
                # Infer component technology
                comp_tech = (
                    f.language or "TypeScript" if "ts" in f.path or "tsx" in f.path else "Python"
                )
                components_map[comp_id] = C4Component(
                    id=comp_id,
                    name=comp_name,
                    container_id=cont_id,
                    technology=comp_tech,
                    description=f"Component handling {comp_name.lower()} operations",
                    source_path=comp_path,
                    symbol_count=0,
                    file_count=0,
                    dependencies=[],
                )

            comp = components_map[comp_id]
            comp.file_count += 1
            comp.symbol_count += sym_count_by_file.get(f.path, len(f.signature or ""))

        # If no containers formed (e.g. empty files), create standard defaults
        if not containers_map:
            containers_map["container_core"] = C4Container(
                id="container_core",
                name="Core Service",
                technology="Python / TypeScript",
                description="Primary repository components",
                container_type="api",
            )

        # Attach database container if relational models exist
        has_db = any(
            "model" in f.path.lower() or "db" in f.path.lower() or "alembic" in f.path.lower()
            for f in files
        )
        if has_db:
            containers_map["container_db"] = C4Container(
                id="container_db",
                name="Relational Database",
                technology="PostgreSQL 16 + pgvector",
                description="Stores repository metadata, AST symbols, commits, and investigation cache",
                container_type="database",
            )

        # Populate components into respective containers
        for comp in components_map.values():
            if comp.container_id in containers_map:
                containers_map[comp.container_id].components.append(comp)

        # 2. Extract Relationships
        relationships: List[C4Relationship] = []
        comp_lookup_by_file: Dict[str, str] = {}
        for comp in components_map.values():
            for f in files:
                if f.path.startswith(comp.source_path):
                    comp_lookup_by_file[f.path] = comp.id

        # External systems
        ext_github = C4System(
            id="sys_github",
            name="GitHub API",
            description="Remote Git repository source, Webhooks, Commits, Pull Requests, Issues",
            external=True,
        )
        ext_llm = C4System(
            id="sys_llm",
            name="OpenRouter / LLM Providers",
            description="External AI models for reasoning and synthesis",
            external=True,
        )
        developer_person = C4Person(
            id="person_dev",
            name="Software Engineer",
            description="Investigates proposed code changes and inspects architecture",
            external=False,
        )

        systems = [ext_github]
        persons = [developer_person]

        # Add LLM external system if investigation engine is present
        has_investigation = any(
            "investigation" in c.source_path.lower() or "llm" in c.source_path.lower()
            for c in components_map.values()
        )
        if has_investigation:
            systems.append(ext_llm)

        # Standard high-level relationships
        relationships.append(
            C4Relationship(
                source_id="person_dev",
                target_id="container_frontend"
                if "container_frontend" in containers_map
                else "container_core",
                description="Uses",
                technology="HTTPS / Browser",
                relationship_type="uses",
            )
        )

        if "container_frontend" in containers_map and "container_backend" in containers_map:
            relationships.append(
                C4Relationship(
                    source_id="container_frontend",
                    target_id="container_backend",
                    description="Fetches architecture and runs investigations",
                    technology="JSON / REST API",
                    relationship_type="calls",
                )
            )

        if "container_backend" in containers_map and "container_db" in containers_map:
            relationships.append(
                C4Relationship(
                    source_id="container_backend",
                    target_id="container_db",
                    description="Reads and writes AST graph and history",
                    technology="Asyncpg / SQLAlchemy",
                    relationship_type="queries",
                )
            )

        if "container_backend" in containers_map:
            relationships.append(
                C4Relationship(
                    source_id="container_backend",
                    target_id="sys_github",
                    description="Pulls Git history and issues",
                    technology="HTTPS REST API",
                    relationship_type="calls",
                )
            )
            if has_investigation:
                relationships.append(
                    C4Relationship(
                        source_id="container_backend",
                        target_id="sys_llm",
                        description="Submits bounded reasoning prompts",
                        technology="OpenRouter API",
                        relationship_type="calls",
                    )
                )

        # Map AST relationships into component-level C4 relationships
        seen_comp_rels = set()
        for rel in context.relationships:
            src_comp_id = comp_lookup_by_file.get(rel.source_path)
            tgt_comp_id = comp_lookup_by_file.get(rel.target_path)
            if src_comp_id and tgt_comp_id and src_comp_id != tgt_comp_id:
                pair = (src_comp_id, tgt_comp_id)
                if pair not in seen_comp_rels:
                    seen_comp_rels.add(pair)
                    # Update component dependencies list
                    if tgt_comp_id in components_map:
                        tgt_name = components_map[tgt_comp_id].name
                        if tgt_name not in components_map[src_comp_id].dependencies:
                            components_map[src_comp_id].dependencies.append(tgt_name)

                    relationships.append(
                        C4Relationship(
                            source_id=src_comp_id,
                            target_id=tgt_comp_id,
                            description=f"{rel.type} ({rel.source_name} -> {rel.target_name})",
                            technology=rel.resolution_method,
                            relationship_type=rel.type,
                        )
                    )

        # Constraints
        constraints_list = []
        for dc in context.design_constraints:
            constraints_list.append(
                {
                    "domain": dc.domain,
                    "priority": dc.priority,
                    "constraint_text": dc.constraint_text,
                    "source_doc_path": dc.source_doc_path,
                }
            )

        return C4ArchitectureModel(
            system_name=repo_name,
            system_description=description,
            persons=persons,
            systems=systems,
            containers=list(containers_map.values()),
            components=list(components_map.values()),
            relationships=relationships,
            constraints=constraints_list,
        )

    @classmethod
    def export_from_architecture_graph(
        cls,
        arch_graph: ArchitectureGraph,
        repo_name: str = "Repository",
        repo_description: Optional[str] = None,
    ) -> C4ArchitectureModel:
        """
        Synthesize C4 model directly from ArchitectureGraph.
        """
        description = repo_description or f"Architecture graph export for {repo_name}"

        # Group components into containers
        containers_map: Dict[str, C4Container] = {}
        components_list: List[C4Component] = []

        for comp_info in arch_graph.major_components:
            path_parts = Path(comp_info.path).parts
            top = path_parts[0].lower() if path_parts else "core"

            if top in ["frontend", "web", "ui", "client"]:
                cont_id = "container_frontend"
                cont_name = "Frontend Application"
                cont_tech = "Next.js / TypeScript"
                cont_type = "web_app"
                cont_desc = "Client web application"
            elif top in ["backend", "server", "api", "app"]:
                cont_id = "container_backend"
                cont_name = "Backend Services"
                cont_tech = "FastAPI / Python"
                cont_type = "api"
                cont_desc = "Server API and intelligence processing"
            elif top in ["packages", "contracts", "shared"]:
                cont_id = "container_contracts"
                cont_name = "Contracts & Shared Packages"
                cont_tech = "TypeScript"
                cont_type = "library"
                cont_desc = "Shared interfaces and contracts"
            else:
                cont_id = "container_core"
                cont_name = "Core Services"
                cont_tech = "Multi-language"
                cont_type = "api"
                cont_desc = "Core application components"

            if cont_id not in containers_map:
                containers_map[cont_id] = C4Container(
                    id=cont_id,
                    name=cont_name,
                    technology=cont_tech,
                    description=cont_desc,
                    container_type=cont_type,
                    path=top,
                )

            c4_comp = C4Component(
                id=f"comp_{_sanitize_id(comp_info.path)}",
                name=comp_info.name,
                container_id=cont_id,
                technology=cont_tech,
                description=f"Component handling {comp_info.name}",
                source_path=comp_info.path,
                symbol_count=comp_info.symbol_count,
                file_count=comp_info.file_count,
                dependencies=comp_info.dependencies,
            )
            components_list.append(c4_comp)
            containers_map[cont_id].components.append(c4_comp)

        if not containers_map:
            containers_map["container_core"] = C4Container(
                id="container_core",
                name="Core Service",
                technology="Multi-language",
                description="Core application components",
                container_type="api",
            )

        # Relationships
        relationships: List[C4Relationship] = []
        for r in arch_graph.relationships:
            relationships.append(
                C4Relationship(
                    source_id=f"comp_{_sanitize_id(r.source_path)}",
                    target_id=f"comp_{_sanitize_id(r.target_path)}",
                    description=f"{r.type} ({r.source_name} -> {r.target_name})",
                    technology=r.resolution_method,
                    relationship_type=r.type,
                )
            )

        developer_person = C4Person(
            id="person_dev",
            name="Developer",
            description="User of the system",
            external=False,
        )

        ext_github = C4System(
            id="sys_github",
            name="GitHub API",
            description="Repository host & VCS",
            external=True,
        )

        return C4ArchitectureModel(
            system_name=repo_name,
            system_description=description,
            persons=[developer_person],
            systems=[ext_github],
            containers=list(containers_map.values()),
            components=components_list,
            relationships=relationships,
        )
