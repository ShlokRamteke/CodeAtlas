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


def _sanitize_text(val: str) -> str:
    """Sanitize string for Mermaid string literals in C4 macros."""
    if not val:
        return ""
    return val.replace('"', "'").replace("\n", " ").strip()


def _sanitize_flowchart_label(val: str) -> str:
    """Sanitize label string for Mermaid flowchart edges (|label|)."""
    if not val:
        return ""
    # Strip characters that break Mermaid flowchart edge parsing:
    # pipes, quotes, parentheses, brackets, braces, arrows
    cleaned = val.replace("|", "/").replace('"', "'").replace("\n", " ")
    cleaned = re.sub(r"[\(\)\[\]\{\}]", "", cleaned)
    cleaned = re.sub(r"-+>+", " to ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _infer_file_technology(path: str, language: Optional[str] = None) -> str:
    """Infer file programming language/runtime from language tag or file extension."""
    if language:
        lang = language.strip().lower()
        if lang in ["javascript", "js"]:
            return "JavaScript"
        if lang in ["typescript", "ts"]:
            return "TypeScript"
        if lang == "python":
            return "Python"
        if lang == "go":
            return "Go"
        if lang == "rust":
            return "Rust"
        if lang in ["java", "kotlin"]:
            return "Java"
        if lang == "ruby":
            return "Ruby"
        if lang == "php":
            return "PHP"
        if lang in ["c#", "csharp"]:
            return "C#"
        return language.title()

    ext = Path(path).suffix.lower()
    if ext in [".js", ".mjs", ".cjs", ".jsx"]:
        return "JavaScript"
    if ext in [".ts", ".tsx"]:
        return "TypeScript"
    if ext == ".py":
        return "Python"
    if ext == ".go":
        return "Go"
    if ext == ".rs":
        return "Rust"
    if ext in [".java", ".kt"]:
        return "Java"
    if ext == ".rb":
        return "Ruby"
    if ext == ".php":
        return "PHP"
    if ext in [".cs"]:
        return "C#"
    if ext in [".html", ".css", ".scss", ".sass", ".vue", ".svelte"]:
        return "Web"
    return "Unknown"


def _detect_container_technology(
    container_type: str,
    container_items: List[Any],
) -> str:
    """Dynamically determine container technology based on its actual files and languages."""
    if not container_items:
        return "Multi-language"

    tech_counts: Dict[str, int] = {}
    has_jsx = False
    has_tsx = False
    has_fastapi = False
    has_flask = False
    has_express = False

    for item in container_items:
        p_str = getattr(item, "path", getattr(item, "source_path", str(item))).lower()
        lang = getattr(item, "language", getattr(item, "technology", None))
        tech = _infer_file_technology(p_str, lang)
        if tech != "Unknown":
            tech_counts[tech] = tech_counts.get(tech, 0) + 1

        if p_str.endswith(".jsx"):
            has_jsx = True
        if p_str.endswith(".tsx"):
            has_tsx = True
        if "fastapi" in p_str:
            has_fastapi = True
        if "flask" in p_str:
            has_flask = True
        if "express" in p_str:
            has_express = True

    if not tech_counts:
        return "Multi-language"

    sorted_techs = sorted(tech_counts.items(), key=lambda x: x[1], reverse=True)
    top_tech, _ = sorted_techs[0]

    # Mixed TypeScript and JavaScript
    if {"TypeScript", "JavaScript"}.issubset(set(tech_counts.keys())):
        primary_lang = "TypeScript / JavaScript"
    else:
        primary_lang = top_tech

    if container_type == "web_app":
        if has_tsx or has_jsx:
            return f"React / {primary_lang}"
        return f"{primary_lang} / Web"

    if container_type == "api":
        if top_tech == "JavaScript":
            return "Node.js / Express" if has_express else "Node.js / JavaScript"
        if top_tech == "TypeScript":
            return "Node.js / TypeScript"
        if top_tech == "Python":
            if has_fastapi:
                return "FastAPI / Python"
            if has_flask:
                return "Flask / Python"
            return "Python"
        if top_tech == "Go":
            return "Go"
        if top_tech == "Rust":
            return "Rust"
        if top_tech == "Java":
            return "Java / Spring Boot"
        return f"{primary_lang} / REST API"

    if container_type == "library":
        return f"{primary_lang}"

    return primary_lang


def _detect_container_description(container_type: str, cont_tech: str) -> str:
    """Generate dynamic container description without hardcoding project specifics."""
    if container_type == "web_app":
        return "Client application, user interface, and frontend views"
    if container_type == "api":
        return f"Backend API, business logic, and server services ({cont_tech})"
    if container_type == "library":
        return "Shared contracts, utility libraries, and reusable models"
    if container_type == "database":
        return "Persistent data storage for application state and records"
    return "Core application business logic and execution components"


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
        declared_node_ids: set[str] = set()

        # Persons
        for p in self.persons:
            tag = "Person_Ext" if p.external else "Person"
            sid = _sanitize_id(p.id)
            declared_node_ids.add(sid)
            lines.append(
                f'  {tag}({sid}, "{_sanitize_text(p.name)}", "{_sanitize_text(p.description)}")'
            )

        # Main system
        main_sys_id = _sanitize_id(self.system_name.lower())
        declared_node_ids.add(main_sys_id)
        lines.append(f'  Enterprise_Boundary(b0, "{_sanitize_text(self.system_name)} Boundary") {{')
        lines.append(
            f'    System({main_sys_id}, "{_sanitize_text(self.system_name)}", "{_sanitize_text(self.system_description)}")'
        )
        lines.append("  }")

        # External systems
        for s in self.systems:
            if s.id != main_sys_id and s.name != self.system_name:
                sid = _sanitize_id(s.id)
                declared_node_ids.add(sid)
                tag = "System_Ext" if s.external else "System"
                lines.append(
                    f'  {tag}({sid}, "{_sanitize_text(s.name)}", "{_sanitize_text(s.description)}")'
                )

        # Internal IDs (containers and components) that map to the main system
        internal_ids = {c.id for c in self.containers} | {comp.id for comp in self.components}

        # Context relationships
        seen_edges = set()
        for r in self.relationships:
            # Normalize internal endpoints to main_sys_id
            src = main_sys_id if r.source_id in internal_ids else _sanitize_id(r.source_id)
            tgt = main_sys_id if r.target_id in internal_ids else _sanitize_id(r.target_id)

            if src != tgt and src in declared_node_ids and tgt in declared_node_ids:
                edge_key = (src, tgt)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    tech = f', "{_sanitize_text(r.technology)}"' if r.technology else ""
                    lines.append(f'  Rel({src}, {tgt}, "{_sanitize_text(r.description)}"{tech})')

        # Fallback relationship from primary person to main system if not already linked
        if self.persons and not any(
            src == _sanitize_id(self.persons[0].id) and tgt == main_sys_id
            for (src, tgt) in seen_edges
        ):
            p0_id = _sanitize_id(self.persons[0].id)
            lines.append(f'  Rel({p0_id}, {main_sys_id}, "Uses", "HTTPS / Browser")')

        return "\n".join(lines)

    def to_mermaid_container(self) -> str:
        """Generate Mermaid C4Container diagram definition."""
        lines = [
            "C4Container",
            f"  title Container Diagram for {self.system_name}",
        ]
        declared_node_ids: set[str] = set()

        for p in self.persons:
            tag = "Person_Ext" if p.external else "Person"
            sid = _sanitize_id(p.id)
            declared_node_ids.add(sid)
            lines.append(
                f'  {tag}({sid}, "{_sanitize_text(p.name)}", "{_sanitize_text(p.description)}")'
            )

        lines.append(f'  Container_Boundary(b_containers, "{_sanitize_text(self.system_name)}") {{')
        for c in self.containers:
            cid = _sanitize_id(c.id)
            declared_node_ids.add(cid)
            if c.container_type == "database":
                tag = "ContainerDb"
            elif c.container_type == "worker":
                tag = "ContainerQueue"
            else:
                tag = "Container"
            lines.append(
                f'    {tag}({cid}, "{_sanitize_text(c.name)}", "{_sanitize_text(c.technology)}", "{_sanitize_text(c.description)}")'
            )
        lines.append("  }")

        for s in self.systems:
            if s.external:
                sid = _sanitize_id(s.id)
                declared_node_ids.add(sid)
                lines.append(
                    f'  System_Ext({sid}, "{_sanitize_text(s.name)}", "{_sanitize_text(s.description)}")'
                )

        rendered_rels = set()
        for r in self.relationships:
            src = r.source_id
            tgt = r.target_id
            # Resolve component to container if needed
            src_c = next((comp.container_id for comp in self.components if comp.id == src), src)
            tgt_c = next((comp.container_id for comp in self.components if comp.id == tgt), tgt)

            s_id = _sanitize_id(src_c)
            t_id = _sanitize_id(tgt_c)

            if s_id != t_id and s_id in declared_node_ids and t_id in declared_node_ids:
                edge_key = (s_id, t_id)
                if edge_key not in rendered_rels:
                    rendered_rels.add(edge_key)
                    tech = f', "{_sanitize_text(r.technology)}"' if r.technology else ""
                    lines.append(f'  Rel({s_id}, {t_id}, "{_sanitize_text(r.description)}"{tech})')

        return "\n".join(lines)

    def to_mermaid_component(self, container_id: Optional[str] = None) -> str:
        """Generate Mermaid C4Component diagram for a specific or primary container."""
        target_container = None
        if container_id:
            target_container = next((c for c in self.containers if c.id == container_id), None)
        if not target_container:
            target_container = next(
                (c for c in self.containers if c.components),
                self.containers[0] if self.containers else None,
            )

        if not target_container:
            return "C4Component\n  title No Components Available"

        lines = [
            "C4Component",
            f"  title Component Diagram for {self.system_name} - {target_container.name}",
            f'  Container_Boundary(b_comp_{_sanitize_id(target_container.id)}, "{_sanitize_text(target_container.name)}") {{',
        ]

        declared_node_ids: set[str] = set()
        target_comp_ids: set[str] = set()

        for comp in target_container.components:
            cid = _sanitize_id(comp.id)
            target_comp_ids.add(comp.id)
            declared_node_ids.add(cid)
            desc = (
                f"{comp.file_count} files, {comp.symbol_count} symbols. {comp.description}".strip()
            )
            lines.append(
                f'    Component({cid}, "{_sanitize_text(comp.name)}", "{_sanitize_text(comp.technology)}", "{_sanitize_text(desc)}")'
            )
        lines.append("  }")

        # Map external connected endpoints to either neighboring containers or external systems
        comp_to_container = {comp.id: comp.container_id for comp in self.components}

        def resolve_endpoint_to_shape(endpoint_id: str) -> Optional[tuple[str, str, str, str]]:
            if endpoint_id in target_comp_ids:
                return ("Component", _sanitize_id(endpoint_id), "", "")
            cont_id = comp_to_container.get(endpoint_id, endpoint_id)
            cont = next((c for c in self.containers if c.id == cont_id), None)
            if cont and cont.id != target_container.id:
                return ("Container", _sanitize_id(cont.id), cont.name, cont.technology or "")
            sys = next((s for s in self.systems if s.id == endpoint_id), None)
            if sys:
                return ("System_Ext", _sanitize_id(sys.id), sys.name, sys.description or "")
            person = next((p for p in self.persons if p.id == endpoint_id), None)
            if person:
                return ("Person", _sanitize_id(person.id), person.name, person.description or "")
            return None

        # Discover external shapes connected to target_container components
        external_shapes: dict[str, tuple[str, str, str, str]] = {}
        for r in self.relationships:
            if r.source_id in target_comp_ids and r.target_id not in target_comp_ids:
                resolved = resolve_endpoint_to_shape(r.target_id)
                if resolved and resolved[0] != "Component":
                    external_shapes[resolved[1]] = resolved
            elif r.target_id in target_comp_ids and r.source_id not in target_comp_ids:
                resolved = resolve_endpoint_to_shape(r.source_id)
                if resolved and resolved[0] != "Component":
                    external_shapes[resolved[1]] = resolved

        # Render external shapes
        for sid, (shape_type, _, name, extra) in external_shapes.items():
            declared_node_ids.add(sid)
            if shape_type == "Container":
                lines.append(
                    f'  Container({sid}, "{_sanitize_text(name)}", "{_sanitize_text(extra)}", "")'
                )
            elif shape_type == "System_Ext":
                lines.append(
                    f'  System_Ext({sid}, "{_sanitize_text(name)}", "{_sanitize_text(extra)}")'
                )
            elif shape_type == "Person":
                lines.append(
                    f'  Person({sid}, "{_sanitize_text(name)}", "{_sanitize_text(extra)}")'
                )

        # Render relationships
        rendered_rels = set()
        for r in self.relationships:
            s_shape = resolve_endpoint_to_shape(r.source_id)
            t_shape = resolve_endpoint_to_shape(r.target_id)
            if not s_shape or not t_shape:
                continue

            s_id = s_shape[1]
            t_id = t_shape[1]

            if s_id != t_id and s_id in declared_node_ids and t_id in declared_node_ids:
                edge_key = (s_id, t_id)
                if edge_key not in rendered_rels:
                    rendered_rels.add(edge_key)
                    tech = f', "{_sanitize_text(r.technology)}"' if r.technology else ""
                    lines.append(f'  Rel({s_id}, {t_id}, "{_sanitize_text(r.description)}"{tech})')

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
                clean_lbl = _sanitize_flowchart_label(r.description or "")
                label = (
                    f"|{clean_lbl}|"
                    if clean_lbl and clean_lbl.lower() not in ["uses", "imports"]
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

        # Collect files by container ID
        container_files_by_id: Dict[str, List[Any]] = {}
        container_meta_by_id: Dict[str, Dict[str, str]] = {}

        for f in files:
            p = Path(f.path)
            parts = p.parts

            # Container detection heuristic
            top_dir = parts[0].lower() if parts else "root"
            if top_dir in ["frontend", "web", "client", "ui"]:
                cont_id = "container_frontend"
                cont_name = "Frontend Application"
                cont_type = "web_app"
            elif top_dir in ["backend", "server", "api", "app"]:
                cont_id = "container_backend"
                cont_name = "Backend API & Services"
                cont_type = "api"
            elif top_dir in ["packages", "contracts", "shared"]:
                cont_id = "container_contracts"
                cont_name = "Shared Packages & Libraries"
                cont_type = "library"
            else:
                cont_id = "container_core"
                cont_name = "Core Application"
                cont_type = "api"

            if cont_id not in container_files_by_id:
                container_files_by_id[cont_id] = []
                container_meta_by_id[cont_id] = {
                    "name": cont_name,
                    "type": cont_type,
                    "path": top_dir,
                }
            container_files_by_id[cont_id].append(f)

            # Component detection heuristic
            # Group by 2 directory levels (e.g. backend/app/investigation or server/controllers)
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
                comp_tech = _infer_file_technology(f.path, f.language)
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

        # Build dynamic containers based on actual member files
        for cont_id, c_files in container_files_by_id.items():
            meta = container_meta_by_id[cont_id]
            cont_tech = _detect_container_technology(meta["type"], c_files)
            cont_desc = _detect_container_description(meta["type"], cont_tech)
            containers_map[cont_id] = C4Container(
                id=cont_id,
                name=meta["name"],
                technology=cont_tech,
                description=cont_desc,
                container_type=meta["type"],
                path=meta["path"],
            )

        # If no containers formed (e.g. empty files), create standard defaults
        if not containers_map:
            containers_map["container_core"] = C4Container(
                id="container_core",
                name="Core Service",
                technology="Multi-language",
                description="Primary repository components",
                container_type="api",
            )

        # Attach database container if relational models exist
        has_db = any(
            "model" in f.path.lower()
            or "db" in f.path.lower()
            or "alembic" in f.path.lower()
            or "prisma" in f.path.lower()
            or "mongoose" in f.path.lower()
            for f in files
        )
        if has_db:
            db_tech = "Relational Database"
            if any("mongo" in f.path.lower() or "mongoose" in f.path.lower() for f in files):
                db_tech = "MongoDB"
            elif any("postgres" in f.path.lower() or "pg" in f.path.lower() for f in files):
                db_tech = "PostgreSQL"
            elif any("sqlite" in f.path.lower() for f in files):
                db_tech = "SQLite"
            elif any("mysql" in f.path.lower() for f in files):
                db_tech = "MySQL"

            containers_map["container_db"] = C4Container(
                id="container_db",
                name="Application Database",
                technology=db_tech,
                description=f"Persistent data storage for application state and records ({db_tech})",
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

                    rel_label = (
                        f"{rel.type.replace('_', ' ')}: {rel.source_name} to {rel.target_name}"
                        if rel.source_name and rel.target_name
                        else rel.type.replace("_", " ")
                    )
                    relationships.append(
                        C4Relationship(
                            source_id=src_comp_id,
                            target_id=tgt_comp_id,
                            description=rel_label,
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
                cont_type = "web_app"
            elif top in ["backend", "server", "api", "app"]:
                cont_id = "container_backend"
                cont_name = "Backend Services"
                cont_type = "api"
            elif top in ["packages", "contracts", "shared"]:
                cont_id = "container_contracts"
                cont_name = "Contracts & Shared Packages"
                cont_type = "library"
            else:
                cont_id = "container_core"
                cont_name = "Core Services"
                cont_type = "api"

            # Dynamic component technology
            comp_tech = _infer_file_technology(comp_info.path)

            c4_comp = C4Component(
                id=f"comp_{_sanitize_id(comp_info.path)}",
                name=comp_info.name,
                container_id=cont_id,
                technology=comp_tech,
                description=f"Component handling {comp_info.name}",
                source_path=comp_info.path,
                symbol_count=comp_info.symbol_count,
                file_count=comp_info.file_count,
                dependencies=comp_info.dependencies,
            )
            components_list.append(c4_comp)

            if cont_id not in containers_map:
                containers_map[cont_id] = C4Container(
                    id=cont_id,
                    name=cont_name,
                    technology=comp_tech,
                    description=_detect_container_description(cont_type, comp_tech),
                    container_type=cont_type,
                    path=top,
                )
            containers_map[cont_id].components.append(c4_comp)

        # Re-evaluate container technology based on all its components
        for cont in containers_map.values():
            cont.technology = _detect_container_technology(cont.container_type, cont.components)
            cont.description = _detect_container_description(cont.container_type, cont.technology)

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
            rel_label = (
                f"{r.type.replace('_', ' ')}: {r.source_name} to {r.target_name}"
                if r.source_name and r.target_name
                else r.type.replace("_", " ")
            )
            relationships.append(
                C4Relationship(
                    source_id=f"comp_{_sanitize_id(r.source_path)}",
                    target_id=f"comp_{_sanitize_id(r.target_path)}",
                    description=rel_label,
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
