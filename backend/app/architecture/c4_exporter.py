from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.context_builder.project_context import ProjectContext
from app.parser.relationship_analyzer import ArchitectureGraph
from app.semantic.container_classifier import ContainerClassifier


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


CODE_EXTENSIONS = {
    ".py",
    ".pyi",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".go",
    ".rs",
    ".java",
    ".kt",
    ".scala",
    ".c",
    ".cpp",
    ".cc",
    ".cxx",
    ".h",
    ".hpp",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".dart",
    ".vue",
    ".svelte",
}

NON_CODE_EXTENSIONS = {
    ".md",
    ".markdown",
    ".txt",
    ".rst",
    ".pdf",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".cnf",
    ".lock",
    ".env",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".webp",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".csv",
    ".tsv",
    ".sql",
    ".sh",
    ".bash",
    ".zsh",
}


def is_architectural_code_file(path: str, language: Optional[str] = None) -> bool:
    """Check if file represents executable application source code rather than documentation/config."""
    p = Path(path)
    name = p.name.lower()
    ext = p.suffix.lower()

    if name.startswith("."):
        return False
    if name in {"license", "copying", "readme", "dockerfile", "makefile", "procfile"}:
        return False
    if any(
        name.endswith(sfx)
        for sfx in [".config.js", ".config.ts", ".config.mjs", ".config.cjs", "rc.js", "rc.ts"]
    ):
        return False
    if ext in NON_CODE_EXTENSIONS:
        return False
    if ext in CODE_EXTENSIONS:
        return True

    if language:
        lang_name = language.strip().lower()
        if lang_name in {
            "python",
            "javascript",
            "typescript",
            "go",
            "rust",
            "java",
            "c",
            "c++",
            "c#",
            "ruby",
            "php",
            "swift",
            "dart",
        }:
            return True

    return False


def _infer_file_technology(path: str, language: Optional[str] = None) -> str:
    """Infer file programming language/runtime from language tag or file extension."""
    ext = Path(path).suffix.lower()
    if ext in NON_CODE_EXTENSIONS:
        return "Unknown"

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
    if ext in [".vue", ".svelte"]:
        return "Web"

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
        if lang in ["json", "yaml", "markdown", "text", "toml", "xml"]:
            return "Unknown"
        return language.title()

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
        has_next = any(
            "next.config" in getattr(item, "path", getattr(item, "source_path", str(item))).lower()
            or "app/page" in getattr(item, "path", getattr(item, "source_path", str(item))).lower()
            or "app/layout"
            in getattr(item, "path", getattr(item, "source_path", str(item))).lower()
            for item in container_items
        )
        if has_next:
            return f"Next.js / {primary_lang}"
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

    if container_type == "worker":
        if top_tech == "Python":
            return (
                "Celery / Python"
                if any(
                    "celery"
                    in getattr(item, "path", getattr(item, "source_path", str(item))).lower()
                    for item in container_items
                )
                else "Python Worker"
            )
        if top_tech in ("TypeScript", "JavaScript"):
            return (
                "BullMQ / TypeScript"
                if any(
                    "bull" in getattr(item, "path", getattr(item, "source_path", str(item))).lower()
                    for item in container_items
                )
                else "Node.js Worker"
            )
        return f"{primary_lang} Worker"

    if container_type == "cli_tool":
        if top_tech == "Go":
            return "Go CLI"
        if top_tech == "Python":
            return "Python CLI"
        if top_tech in ("TypeScript", "JavaScript"):
            return "Node.js CLI"
        return f"{primary_lang} CLI"

    if container_type in ("library", "shared_library"):
        return f"{primary_lang}"

    if container_type == "database":
        return "Relational Database"

    return primary_lang


def _detect_container_description(container_type: str, cont_tech: str) -> str:
    """Generate dynamic container description without hardcoding project specifics."""
    if container_type == "web_app":
        return f"Client web application, user interface, and frontend views ({cont_tech})"
    if container_type == "api":
        return f"Backend API, business logic, and server services ({cont_tech})"
    if container_type in ("library", "shared_library"):
        return f"Shared contracts, utility libraries, and reusable models ({cont_tech})"
    if container_type == "worker":
        return f"Background task processor and asynchronous job queue worker ({cont_tech})"
    if container_type == "cli_tool":
        return f"Command-line interface utility and developer tool ({cont_tech})"
    if container_type == "database":
        return f"Persistent data storage for application state and records ({cont_tech})"
    return f"Core application business logic and execution components ({cont_tech})"


def _detect_repository_layout(all_entities: List[Any]) -> str:
    """Detect overall architecture layout pattern of the repository.

    Returns:
    - 'monorepo': Explicit frontend and backend containers
    - 'frontend_app': Unified client web application (Next.js, React, Vue, Vite, etc.)
    - 'backend_app': Unified API/server application (Node/Express, FastAPI, Django, etc.)
    - 'monorepo_packages': Multi-package monorepo (packages/* or services/*)
    - 'standard': General multi-directory application
    """
    all_paths = [getattr(e, "path", str(e)) for e in all_entities]
    all_paths_lower = [p.lower() for p in all_paths]
    top_dirs = {Path(p).parts[0].lower() for p in all_paths if len(Path(p).parts) > 1}
    dir_segments = {part.lower() for p in all_paths for part in Path(p).parts[:-1]}

    has_explicit_frontend = bool(top_dirs & {"frontend", "client", "web", "ui"})
    has_explicit_backend = bool(top_dirs & {"backend", "server", "api"})

    if has_explicit_frontend and has_explicit_backend:
        return "monorepo"

    # Frontend app detection (Next.js, React, Vite, Vue, etc.)
    frontend_config_files = {
        "next.config.js",
        "next.config.mjs",
        "next.config.ts",
        "vite.config.js",
        "vite.config.ts",
        "nuxt.config.ts",
        "remix.config.js",
        "astro.config.mjs",
    }
    is_frontend_config = any(Path(p).name.lower() in frontend_config_files for p in all_paths_lower)
    frontend_dir_signals = {"components", "hooks", "screens", "views", "styles", "widgets"}
    has_frontend_dirs = bool((top_dirs | dir_segments) & frontend_dir_signals)
    has_jsx_tsx = any(p.endswith(".tsx") or p.endswith(".jsx") for p in all_paths_lower)

    # In Next.js, app/ is the frontend App Router if it contains tsx/jsx or standard routes
    has_nextjs_app_router = "app" in top_dirs and (
        has_jsx_tsx
        or any("app/page." in p or "app/layout." in p or "app/route." in p for p in all_paths_lower)
    )

    # Backend in app/ signal (Python FastAPI/Django/Flask, Go, etc.)
    has_backend_app_dir = "app" in top_dirs and any(
        (p.startswith("app/") or p.startswith("app\\"))
        and any(p.endswith(ext) for ext in [".py", ".go", ".rs", ".rb", ".java", ".php"])
        for p in all_paths_lower
    )

    backend_dir_signals = {
        "controllers",
        "routes",
        "models",
        "middleware",
        "handlers",
        "resolvers",
    }
    has_backend_dirs = bool((top_dirs | dir_segments) & backend_dir_signals)

    if (
        (is_frontend_config or has_frontend_dirs or has_nextjs_app_router or has_jsx_tsx)
        and not has_explicit_backend
        and not has_backend_app_dir
        and not (has_backend_dirs and not has_jsx_tsx and not is_frontend_config)
    ):
        return "frontend_app"

    if (
        (has_explicit_backend or has_backend_dirs or has_backend_app_dir)
        and not has_explicit_frontend
        and not has_frontend_dirs
    ):
        return "backend_app"

    if has_explicit_frontend:
        return "frontend_app"

    if bool(top_dirs & {"packages", "services", "libs", "apps", "cmd", "workers", "modules"}):
        return "monorepo_packages"

    return "standard"


def _infer_component_info(
    file_path: str,
    repo_layout: str,
    container_roles_map: Optional[Dict[str, str]] = None,
) -> tuple[str, str, str, str, str]:
    """Dynamically determine (cont_id, cont_name, cont_type, comp_path, comp_name) for any file.

    Ensures all repositories (frontend, backend, monorepo, packages) partition their code
    cleanly into semantic architectural components.
    """
    p = Path(file_path)
    parts = p.parts
    top = parts[0].lower() if len(parts) > 1 else ""

    # Multi-package / multi-service directory check
    is_multi_package = (
        top
        in [
            "packages",
            "services",
            "apps",
            "libs",
            "cmd",
            "workers",
            "modules",
        ]
        and len(parts) >= 2
    )
    pkg = parts[1] if is_multi_package else ""

    # 1. Determine container
    if is_multi_package and (
        repo_layout in ("monorepo_packages", "monorepo", "standard")
        or top in ("packages", "services", "apps", "cmd", "workers")
    ):
        cont_id = f"container_{_sanitize_id(pkg)}"
        if container_roles_map and cont_id in container_roles_map:
            cont_type = container_roles_map[cont_id]
        else:
            classified = ContainerClassifier.heuristic_classify(
                f"{top}/{pkg}",
                files=[file_path],
            )
            cont_type = classified.value

        role_suffix_map = {
            "web_app": "Application",
            "api": "Service",
            "worker": "Worker",
            "database": "Database",
            "shared_library": "Library",
            "library": "Library",
            "cli_tool": "CLI",
        }
        suffix = role_suffix_map.get(cont_type, "Package")
        clean_pkg_title = pkg.replace("-", " ").replace("_", " ").title()
        if clean_pkg_title.lower().endswith(suffix.lower()):
            cont_name = clean_pkg_title
        else:
            cont_name = f"{clean_pkg_title} {suffix}"
    elif repo_layout == "frontend_app":
        cont_id = "container_frontend"
        cont_name = "Frontend Web Application"
        cont_type = "web_app"
    elif repo_layout == "backend_app":
        cont_id = "container_backend"
        cont_name = "Backend API & Services"
        cont_type = "api"
    else:
        stem = p.stem.lower()
        if top in ["frontend", "web", "client", "ui"] or (
            len(parts) == 1 and stem in ["index", "client", "ui", "web"]
        ):
            cont_id = "container_frontend"
            cont_name = "Frontend Application"
            cont_type = "web_app"
        elif top in ["backend", "server", "api"] or (
            len(parts) == 1 and stem in ["server", "api", "backend", "main"]
        ):
            cont_id = "container_backend"
            cont_name = "Backend API & Services"
            cont_type = "api"
        elif top in ["worker", "consumer", "celery", "jobs"]:
            cont_id = "container_worker"
            cont_name = "Background Worker"
            cont_type = "worker"
        elif top in ["cmd", "cli", "bin", "tools"]:
            cont_id = "container_cli"
            cont_name = "CLI Tool"
            cont_type = "cli_tool"
        elif top in ["packages", "contracts", "shared", "libs"]:
            cont_id = "container_contracts"
            cont_name = "Shared Packages & Libraries"
            cont_type = "shared_library"
        elif top == "app":
            if any(file_path.endswith(ext) for ext in [".py", ".go", ".rs", ".rb"]):
                cont_id = "container_backend"
                cont_name = "Backend API & Services"
                cont_type = "api"
            else:
                cont_id = "container_frontend"
                cont_name = "Frontend Application"
                cont_type = "web_app"
        else:
            classified = ContainerClassifier.heuristic_classify(top or str(p.parent), [file_path])
            cont_id = f"container_{_sanitize_id(top or 'core')}"
            cont_name = f"{(top or 'core').replace('-', ' ').replace('_', ' ').title()} Service"
            cont_type = classified.value

    # 2. Determine component path and name
    subparts = list(parts)
    wrapper_prefix = ""
    container_prefixes = [
        "frontend",
        "backend",
        "server",
        "client",
        "web",
        "ui",
        "packages",
        "services",
        "apps",
        "libs",
        "cmd",
        "workers",
        "modules",
    ]
    if len(subparts) > 1 and subparts[0].lower() in container_prefixes:
        if (
            subparts[0].lower()
            in [
                "packages",
                "services",
                "apps",
                "libs",
                "cmd",
                "workers",
                "modules",
            ]
            and len(subparts) > 2
        ):
            wrapper_prefix = f"{subparts[0]}/{subparts[1]}"
            subparts = subparts[2:]
        else:
            wrapper_prefix = subparts[0]
            subparts = subparts[1:]

    inner_prefix = ""
    if len(subparts) > 1 and subparts[0].lower() in ["src", "internal", "pkg"]:
        inner_prefix = subparts[0]
        subparts = subparts[1:]
    elif len(subparts) > 2 and subparts[0].lower() == "app" and cont_type != "web_app":
        inner_prefix = subparts[0]
        subparts = subparts[1:]

    # Check if Next.js App Router (app/ containing pages/routes)
    if subparts and subparts[0].lower() == "app" and cont_type == "web_app":
        comp_path_parts = [p for p in [wrapper_prefix, inner_prefix, "app"] if p]
        comp_path = "/".join(comp_path_parts)
        comp_name = "App Router (Pages & Routes)"
    elif subparts and len(subparts) >= 2:
        layer = subparts[0].lower()
        comp_path_parts = [p for p in [wrapper_prefix, inner_prefix, subparts[0]] if p]
        comp_path = "/".join(comp_path_parts)

        layer_names = {
            "app": "App Router (Pages & Routes)"
            if cont_type == "web_app"
            else "Core Application Services",
            "pages": "Pages & Routes",
            "routes": "API Endpoints & Routing",
            "endpoints": "API Endpoints & Routing",
            "api": "API Endpoints & Routing" if cont_type == "api" else "API Client Services",
            "controllers": "Controllers",
            "models": "Data Models & Schemas",
            "schemas": "Data Models & Schemas",
            "entities": "Data Models & Schemas",
            "services": "Business Logic Services",
            "middleware": "Middleware & Auth",
            "components": "UI Components",
            "hooks": "State & Lifecycle Hooks",
            "lib": "Utilities & Libraries",
            "utils": "Utilities & Libraries",
            "helpers": "Utilities & Helpers",
            "db": "Database & Storage",
            "database": "Database & Storage",
            "repository": "Repositories & Persistence",
            "repositories": "Repositories & Persistence",
            "core": "Core Configuration",
            "config": "Core Configuration",
            "store": "State Management",
            "stores": "State Management",
            "styles": "Styles & Design Tokens",
        }
        comp_name = layer_names.get(layer, layer.replace("_", " ").title())
    elif subparts and len(subparts) == 1:
        comp_path = file_path
        comp_name = p.stem.replace("_", " ").title()
    else:
        comp_path = file_path
        comp_name = p.stem.replace("_", " ").title()

    return cont_id, cont_name, cont_type, comp_path, comp_name


def _find_component_for_path(
    path: str,
    components_map: Dict[str, C4Component],
    comp_lookup_by_file: Dict[str, str],
    source_path: Optional[str] = None,
) -> Optional[str]:
    """Resolve a target path (file, alias @/, ~/, or relative import) to a C4 component ID."""
    if not path:
        return None

    # 1. Exact match in file-to-component lookup
    if path in comp_lookup_by_file:
        return comp_lookup_by_file[path]

    # 2. Exact match in component IDs
    if path in components_map:
        return path

    # 3. Direct component source_path match
    for cid, comp in components_map.items():
        if comp.source_path == path or comp.source_path == path.strip("/"):
            return cid

    # 4. Normalize aliases and relative paths
    clean = path.strip()
    if clean.startswith(("@/", "~/", "#/", "$lib/")):
        clean = clean.split("/", 1)[1] if "/" in clean else clean
    elif clean.startswith(".") and source_path:
        try:
            clean = os.path.normpath(str(Path(source_path).parent / clean)).replace("\\", "/")
        except Exception:
            pass
    elif "." in clean and not any(
        clean.endswith(ext)
        for ext in [".js", ".ts", ".jsx", ".tsx", ".py", ".css", ".json", ".mjs"]
    ):
        clean = clean.replace(".", "/")

    clean = clean.lstrip("/")

    # Check normalized in lookup
    if clean in comp_lookup_by_file:
        return comp_lookup_by_file[clean]

    # Check with extensions in lookup
    for ext in [
        "",
        ".tsx",
        ".ts",
        ".jsx",
        ".js",
        ".py",
        ".go",
        ".rs",
        ".vue",
        ".svelte",
        "/index.tsx",
        "/index.ts",
        "/index.js",
        "/__init__.py",
    ]:
        cand = f"{clean}{ext}"
        if cand in comp_lookup_by_file:
            return comp_lookup_by_file[cand]

    # 5. Check component source_path prefix matching (longest first)
    sorted_comps = sorted(
        components_map.values(),
        key=lambda c: len(c.source_path),
        reverse=True,
    )

    clean_lower = clean.lower()
    for comp in sorted_comps:
        comp_sp = comp.source_path.lower().strip("/")
        comp_sp_bare = comp_sp[4:] if comp_sp.startswith("src/") else comp_sp

        if clean_lower.startswith(comp_sp) or clean_lower.startswith(comp_sp_bare):
            return comp.id

        clean_parts = Path(clean_lower).parts
        if comp_sp in clean_parts or comp_sp_bare in clean_parts:
            return comp.id

    # 6. Check component name or stem matching
    clean_stem = Path(clean).stem.lower()
    for comp in sorted_comps:
        if comp.name.lower() == clean_stem or Path(comp.source_path).stem.lower() == clean_stem:
            return comp.id

    return None


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
    symbol_roles: Dict[str, int] = field(default_factory=dict)
    dominant_role: Optional[str] = None


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

        # Determine which external systems are actually connected to containers
        container_ids = {c.id for c in self.containers}
        connected_system_ids = set()
        for r in self.relationships:
            src_c = next(
                (comp.container_id for comp in self.components if comp.id == r.source_id),
                r.source_id,
            )
            tgt_c = next(
                (comp.container_id for comp in self.components if comp.id == r.target_id),
                r.target_id,
            )
            if src_c in container_ids and tgt_c not in container_ids:
                connected_system_ids.add(_sanitize_id(tgt_c))
            elif tgt_c in container_ids and src_c not in container_ids:
                connected_system_ids.add(_sanitize_id(src_c))

        for s in self.systems:
            if s.external:
                sid = _sanitize_id(s.id)
                if sid in connected_system_ids:
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

        # Connect Person to primary entrypoint component if person connects to this container
        for r in self.relationships:
            if r.source_id in [p.id for p in self.persons] and r.target_id == target_container.id:
                entry_comp = next(
                    (
                        c
                        for c in target_container.components
                        if any(
                            k in c.source_path.lower()
                            for k in [
                                "app",
                                "router",
                                "route",
                                "page",
                                "main",
                                "index",
                                "controller",
                            ]
                        )
                    ),
                    target_container.components[0] if target_container.components else None,
                )
                if entry_comp:
                    p_obj = next(p for p in self.persons if p.id == r.source_id)
                    p_sid = _sanitize_id(p_obj.id)
                    if p_sid not in declared_node_ids:
                        declared_node_ids.add(p_sid)
                        lines.append(
                            f'  Person({p_sid}, "{_sanitize_text(p_obj.name)}", "{_sanitize_text(p_obj.description)}")'
                        )
                    entry_sid = _sanitize_id(entry_comp.id)
                    edge_key = (p_sid, entry_sid)
                    if edge_key not in rendered_rels:
                        rendered_rels.add(edge_key)
                        tech = f', "{_sanitize_text(r.technology)}"' if r.technology else ""
                        lines.append(
                            f'  Rel({p_sid}, {entry_sid}, "{_sanitize_text(r.description)}"{tech})'
                        )

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
        container_roles: Optional[Dict[str, str]] = None,
        container_classifier: Optional[ContainerClassifier] = None,
    ) -> C4ArchitectureModel:
        """
        Synthesize C4 model from canonical ProjectContext.
        """
        description = repo_description or context.summary or f"Architecture model for {repo_name}"

        # 1. Identify containers
        containers_map: Dict[str, C4Container] = {}
        components_map: Dict[str, C4Component] = {}
        all_entities = context.entities
        classifier = container_classifier or ContainerClassifier()

        # Collect manifest files for contextual container evaluation
        manifest_by_dir: Dict[str, str] = {}
        for e in all_entities:
            if getattr(e, "kind", None) == "file":
                p_obj = Path(getattr(e, "path", ""))
                if p_obj.name.lower() in (
                    "package.json",
                    "pyproject.toml",
                    "dockerfile",
                    "cargo.toml",
                    "go.mod",
                ):
                    parent_key = str(p_obj.parent).replace("\\", "/").strip(".")
                    manifest_by_dir[parent_key] = p_obj.name.lower()

        # File and symbol entities
        files = [e for e in all_entities if e.kind == "file"]
        symbols = [e for e in all_entities if e.kind == "symbol"]

        # Filter to architectural code files, ignoring documentation, config, lockfiles
        code_files = [f for f in files if is_architectural_code_file(f.path, f.language)]
        files_to_process = code_files if code_files else files

        # Count symbols and collect roles by file path
        sym_count_by_file: Dict[str, int] = {}
        sym_roles_by_file: Dict[str, List[str]] = {}
        for s in symbols:
            sym_count_by_file[s.path] = sym_count_by_file.get(s.path, 0) + 1
            role = getattr(s, "architectural_role", None)
            if role:
                role_str = role.value if hasattr(role, "value") else str(role)
                sym_roles_by_file.setdefault(s.path, []).append(role_str)

        # Collect files by container ID
        container_files_by_id: Dict[str, List[Any]] = {}
        container_meta_by_id: Dict[str, Dict[str, str]] = {}

        repo_layout = _detect_repository_layout(all_entities)

        for f in files_to_process:
            cont_id, cont_name, cont_type, comp_path, comp_name = _infer_component_info(
                f.path, repo_layout, container_roles_map=container_roles
            )
            p_parts = Path(f.path).parts
            if len(p_parts) > 2 and p_parts[0].lower() in [
                "packages",
                "services",
                "apps",
                "libs",
                "cmd",
                "workers",
                "modules",
            ]:
                cont_dir = f"{p_parts[0]}/{p_parts[1]}"
            elif len(p_parts) > 1:
                cont_dir = p_parts[0]
            else:
                cont_dir = cont_id.replace("container_", "")

            if cont_id not in container_files_by_id:
                container_files_by_id[cont_id] = []
                container_meta_by_id[cont_id] = {
                    "name": cont_name,
                    "type": cont_type,
                    "path": cont_dir,
                }
            container_files_by_id[cont_id].append(f)

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
            for role_str in sym_roles_by_file.get(f.path, []):
                comp.symbol_roles[role_str] = comp.symbol_roles.get(role_str, 0) + 1

        for comp in components_map.values():
            if comp.symbol_roles:
                comp.dominant_role = max(comp.symbol_roles.items(), key=lambda kv: kv[1])[0]

        # Build dynamic containers based on actual member files
        for cont_id, c_files in container_files_by_id.items():
            meta = container_meta_by_id[cont_id]
            c_paths = [getattr(cf, "path", str(cf)) for cf in c_files]

            if container_roles and cont_id in container_roles:
                cont_type = container_roles[cont_id]
            elif meta["type"] in (
                "web_app",
                "api",
                "worker",
                "cli_tool",
                "shared_library",
                "database",
            ):
                cont_type = meta["type"]
            else:
                manifest_hint = manifest_by_dir.get(meta["path"])
                detected_role = classifier.heuristic_classify(
                    meta["path"],
                    c_paths,
                    manifest_content=manifest_hint,
                )
                cont_type = (
                    detected_role.value if hasattr(detected_role, "value") else str(detected_role)
                )

            cont_tech = _detect_container_technology(cont_type, c_files)
            cont_desc = _detect_container_description(cont_type, cont_tech)
            containers_map[cont_id] = C4Container(
                id=cont_id,
                name=meta["name"],
                technology=cont_tech,
                description=cont_desc,
                container_type=cont_type,
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

        # Attach database container if models exist (and not a pure frontend app unless DB client detected)
        has_db_client = any(
            "prisma" in f.path.lower()
            or "mongoose" in f.path.lower()
            or "alembic" in f.path.lower()
            or "dexie" in f.path.lower()
            or "supabase" in f.path.lower()
            for f in files
        )
        has_db_model = any("model" in f.path.lower() or "db" in f.path.lower() for f in files)
        has_db = has_db_client or (has_db_model and repo_layout != "frontend_app")

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
        has_github_integration = any(
            "github" in f.path.lower() or "octokit" in f.path.lower() for f in files
        ) or any("github" in getattr(s, "name", "").lower() for s in symbols)

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

        # Developer / User persona
        if repo_layout == "frontend_app":
            developer_person = C4Person(
                id="person_dev",
                name="User",
                description="Interacts with the web application via browser",
                external=False,
            )
        elif repo_layout == "backend_app":
            developer_person = C4Person(
                id="person_dev",
                name="API Client / Developer",
                description="Consumes REST / GraphQL API endpoints",
                external=False,
            )
        else:
            developer_person = C4Person(
                id="person_dev",
                name="Software Engineer",
                description="Interacts with system workflows and applications",
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
        target_person_cont = (
            "container_frontend"
            if "container_frontend" in containers_map
            else (
                "container_backend" if "container_backend" in containers_map else "container_core"
            )
        )
        relationships.append(
            C4Relationship(
                source_id="person_dev",
                target_id=target_person_cont,
                description="Uses"
                if target_person_cont == "container_frontend"
                else "Interacts with",
                technology="HTTPS / Browser"
                if target_person_cont == "container_frontend"
                else "HTTPS / REST API",
                relationship_type="uses",
            )
        )

        if "container_frontend" in containers_map and "container_backend" in containers_map:
            relationships.append(
                C4Relationship(
                    source_id="container_frontend",
                    target_id="container_backend",
                    description="Fetches data and executes application workflows",
                    technology="JSON / REST API",
                    relationship_type="calls",
                )
            )

        if "container_backend" in containers_map and "container_db" in containers_map:
            relationships.append(
                C4Relationship(
                    source_id="container_backend",
                    target_id="container_db",
                    description="Reads and writes persistent data",
                    technology=containers_map["container_db"].technology,
                    relationship_type="queries",
                )
            )

        if has_github_integration:
            gh_caller = (
                "container_backend" if "container_backend" in containers_map else target_person_cont
            )
            relationships.append(
                C4Relationship(
                    source_id=gh_caller,
                    target_id="sys_github",
                    description="Integrates with Git repository & issues",
                    technology="HTTPS REST API",
                    relationship_type="calls",
                )
            )

        if has_investigation:
            inv_caller = (
                "container_backend" if "container_backend" in containers_map else target_person_cont
            )
            relationships.append(
                C4Relationship(
                    source_id=inv_caller,
                    target_id="sys_llm",
                    description="Submits bounded reasoning prompts",
                    technology="OpenRouter API",
                    relationship_type="calls",
                )
            )

        # Map AST relationships into component-level C4 relationships
        seen_comp_rels = set()
        for rel in context.relationships:
            src_comp_id = _find_component_for_path(
                rel.source_path, components_map, comp_lookup_by_file
            )
            tgt_comp_id = _find_component_for_path(
                rel.target_path, components_map, comp_lookup_by_file, source_path=rel.source_path
            )
            if src_comp_id and tgt_comp_id and src_comp_id != tgt_comp_id:
                pair = (src_comp_id, tgt_comp_id)
                if pair not in seen_comp_rels:
                    seen_comp_rels.add(pair)
                    # Update component dependencies list
                    if tgt_comp_id in components_map and src_comp_id in components_map:
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
                            technology=rel.resolution_method or "ast_import_resolver",
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
    async def export_from_project_context_async(
        cls,
        context: ProjectContext,
        repo_name: str = "Repository",
        repo_description: Optional[str] = None,
        container_classifier: Optional[ContainerClassifier] = None,
    ) -> C4ArchitectureModel:
        """Asynchronously synthesize C4 model with System One batch container classification."""
        classifier = container_classifier or ContainerClassifier()
        all_entities = context.entities
        files = [e for e in all_entities if e.kind == "file"]
        code_files = [f for f in files if is_architectural_code_file(f.path, f.language)]
        files_to_process = code_files if code_files else files
        repo_layout = _detect_repository_layout(all_entities)

        # Preliminary pass to discover candidate container directories
        cont_files: Dict[str, List[str]] = {}
        for f in files_to_process:
            cont_id, _, _, _, _ = _infer_component_info(f.path, repo_layout)
            cont_files.setdefault(cont_id, []).append(f.path)

        candidates = [
            {
                "path": cid.replace("container_", ""),
                "files": flist,
            }
            for cid, flist in cont_files.items()
        ]
        batch_results = await classifier.classify_containers_batch(candidates)
        container_roles = {
            f"container_{_sanitize_id(path)}": res.role.value for path, res in batch_results.items()
        }

        return cls.export_from_project_context(
            context=context,
            repo_name=repo_name,
            repo_description=repo_description,
            container_roles=container_roles,
            container_classifier=classifier,
        )

    @classmethod
    def export_from_architecture_graph(
        cls,
        arch_graph: ArchitectureGraph,
        repo_name: str = "Repository",
        repo_description: Optional[str] = None,
        container_roles: Optional[Dict[str, str]] = None,
        container_classifier: Optional[ContainerClassifier] = None,
    ) -> C4ArchitectureModel:
        """
        Synthesize C4 model directly from ArchitectureGraph.
        """
        description = repo_description or f"Architecture graph export for {repo_name}"

        # Group components into containers
        containers_map: Dict[str, C4Container] = {}
        components_list: List[C4Component] = []

        repo_layout = _detect_repository_layout(arch_graph.major_components)

        for comp_info in arch_graph.major_components:
            if not is_architectural_code_file(comp_info.path):
                continue

            cont_id, cont_name, cont_type, comp_path, comp_name = _infer_component_info(
                comp_info.path, repo_layout, container_roles_map=container_roles
            )
            top = cont_id.replace("container_", "")
            comp_tech = _infer_file_technology(comp_info.path)

            c4_comp = C4Component(
                id=f"comp_{_sanitize_id(comp_path)}",
                name=comp_name,
                container_id=cont_id,
                technology=comp_tech,
                description=f"Component handling {comp_name.lower()} operations",
                source_path=comp_path,
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

        # Build comp_lookup_by_file and components_map
        comp_lookup_by_file: Dict[str, str] = {}
        for comp in components_list:
            comp_lookup_by_file[comp.source_path] = comp.id
        components_map = {c.id: c for c in components_list}

        # Relationships
        relationships: List[C4Relationship] = []
        seen_comp_rels = set()
        for r in arch_graph.relationships:
            src_comp_id = _find_component_for_path(
                r.source_path, components_map, comp_lookup_by_file
            )
            tgt_comp_id = _find_component_for_path(
                r.target_path, components_map, comp_lookup_by_file, source_path=r.source_path
            )
            if src_comp_id and tgt_comp_id and src_comp_id != tgt_comp_id:
                pair = (src_comp_id, tgt_comp_id)
                if pair not in seen_comp_rels:
                    seen_comp_rels.add(pair)
                    if tgt_comp_id in components_map and src_comp_id in components_map:
                        tgt_name = components_map[tgt_comp_id].name
                        if tgt_name not in components_map[src_comp_id].dependencies:
                            components_map[src_comp_id].dependencies.append(tgt_name)

                    rel_label = (
                        f"{r.type.replace('_', ' ')}: {r.source_name} to {r.target_name}"
                        if r.source_name and r.target_name
                        else r.type.replace("_", " ")
                    )
                    relationships.append(
                        C4Relationship(
                            source_id=src_comp_id,
                            target_id=tgt_comp_id,
                            description=rel_label,
                            technology=r.resolution_method or "ast_import_resolver",
                            relationship_type=r.type,
                        )
                    )

        # Persona
        if repo_layout == "frontend_app":
            developer_person = C4Person(
                id="person_dev",
                name="User",
                description="Interacts with the web application via browser",
                external=False,
            )
        elif repo_layout == "backend_app":
            developer_person = C4Person(
                id="person_dev",
                name="API Client / Developer",
                description="Consumes backend APIs and services",
                external=False,
            )
        else:
            developer_person = C4Person(
                id="person_dev",
                name="Developer",
                description="User of the system",
                external=False,
            )

        target_person_container = (
            "container_frontend"
            if "container_frontend" in containers_map
            else (
                "container_backend" if "container_backend" in containers_map else "container_core"
            )
        )
        if target_person_container in containers_map:
            relationships.append(
                C4Relationship(
                    source_id="person_dev",
                    target_id=target_person_container,
                    description="Uses"
                    if target_person_container == "container_frontend"
                    else "Interacts with",
                    technology="HTTPS / Browser"
                    if target_person_container == "container_frontend"
                    else "HTTPS / REST API",
                    relationship_type="uses",
                )
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
