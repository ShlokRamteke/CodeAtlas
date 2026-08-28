from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class ComponentBrief:
    name: str
    path: str
    language: str
    symbol_count: int
    symbols: List[Dict[str, str]]
    dependencies: List[Dict[str, str]]
    callers: List[Dict[str, str]]
    tests: List[str]
    human_summary: str
    llm_context: str


@dataclass
class RepositoryBrief:
    repository_id: str
    full_name: str
    file_count: int
    symbol_count: int
    dependency_count: int
    languages: Dict[str, int]
    components: List[ComponentBrief]
    human_summary: str
    llm_context: str


class CurrentSystemContextBuilder:
    """
    Constructs compact, trustworthy current-system briefings for humans
    and token-efficient context blocks for LLM reasoning.
    """

    def build_component_brief(
        self,
        component_path: str,
        files: List[dict],
        symbols: List[dict],
        dependencies: List[dict],
        relationships: List[dict],
    ) -> ComponentBrief:
        # Filter files belonging to this component or exact path
        matching_files = [
            f for f in files
            if f.get("path", "").startswith(component_path) or Path(f.get("path", "")).stem.lower() == component_path.lower()
        ]
        if not matching_files and files:
            matching_files = files[:5]

        file_ids = {f.get("id") for f in matching_files if f.get("id")}
        comp_symbols = [s for s in symbols if s.get("file_id") in file_ids]

        # Determine primary language
        langs = [f.get("language", "typescript") for f in matching_files if f.get("language")]
        primary_lang = langs[0] if langs else "typescript"

        # Outbound dependencies
        outbound_deps: List[Dict[str, str]] = []
        for dep in dependencies:
            if dep.get("source_file_id") in file_ids:
                outbound_deps.append({
                    "target": dep.get("target_path", ""),
                    "symbol": dep.get("imported_symbol") or "",
                    "kind": str(dep.get("kind", "internal")),
                    "confidence": "1.0",
                })

        # Inbound callers (other components importing these files)
        file_paths = {f.get("path") for f in matching_files}
        callers: List[Dict[str, str]] = []
        for rel in relationships:
            if rel.get("target_path") in file_paths and rel.get("type") in ["imports", "calls"]:
                callers.append({
                    "caller": rel.get("source_name", ""),
                    "path": rel.get("source_path", ""),
                    "type": rel.get("type", "imports"),
                })

        # Tests
        tests: List[str] = []
        for rel in relationships:
            if rel.get("source_path") in file_paths and rel.get("type") == "tested_by":
                tests.append(rel.get("target_path", ""))

        # 1. Generate Human Markdown Summary
        sym_list_md = "\n".join(
            f"- `{s.get('kind', 'symbol')}` **{s.get('name', '')}** (lines {s.get('line_start', 1)}-{s.get('line_end', 1)})"
            for s in comp_symbols[:10]
        ) or "- *No symbols indexed*"

        dep_list_md = "\n".join(
            f"- `{d['target']}`" + (f" (imports `{d['symbol']}`)" if d['symbol'] else "") + f" [{d['kind']}]"
            for d in outbound_deps[:10]
        ) or "- *None (Standalone module)*"

        caller_list_md = "\n".join(
            f"- **{c['caller']}** (`{c['path']}`)" for c in callers[:10]
        ) or "- *No internal callers discovered*"

        test_list_md = "\n".join(
            f"- `{t}`" for t in tests
        ) or "- *No associated test file match*"

        human_summary = f"""### Component: {component_path}
**Primary Language:** {primary_lang.capitalize()} | **Source Files:** {len(matching_files)} | **Symbols:** {len(comp_symbols)}

#### 📦 Key Symbols
{sym_list_md}

#### 🔗 Dependencies (Imports)
{dep_list_md}

#### 📥 Used By (Inbound Callers)
{caller_list_md}

#### 🧪 Linked Test Suites
{test_list_md}
"""

        # 2. Generate LLM Context Block
        sym_names = [f"{s.get('name')}({s.get('kind')})" for s in comp_symbols[:12]]
        dep_names = [f"{d['target']}:{d['symbol']}" if d['symbol'] else d['target'] for d in outbound_deps[:10]]
        caller_names = [f"{c['caller']}({c['path']})" for c in callers[:8]]

        llm_context = f"""--- CURRENT SYSTEM CONTEXT BRIEFING ---
TARGET COMPONENT: {component_path}
LANGUAGE: {primary_lang}
SYMBOLS ({len(comp_symbols)}): [{', '.join(sym_names)}]
OUTBOUND DEPENDENCIES: [{', '.join(dep_names)}]
INBOUND CALLERS: [{', '.join(caller_names)}]
LINKED TESTS: [{', '.join(tests) if tests else 'none'}]
EXTRACTION PROVENANCE: Tree-sitter AST (Confidence: 1.0)
----------------------------------------"""

        return ComponentBrief(
            name=component_path,
            path=component_path,
            language=primary_lang,
            symbol_count=len(comp_symbols),
            symbols=[{"name": s.get("name", ""), "kind": s.get("kind", ""), "signature": s.get("signature", "")} for s in comp_symbols],
            dependencies=outbound_deps,
            callers=callers,
            tests=tests,
            human_summary=human_summary,
            llm_context=llm_context,
        )

    def build_repository_brief(
        self,
        repository_id: str,
        full_name: str,
        files: List[dict],
        symbols: List[dict],
        dependencies: List[dict],
        relationships: List[dict],
        languages: Dict[str, int],
    ) -> RepositoryBrief:
        components: List[ComponentBrief] = []

        # Find distinct top-level components
        comp_paths = set()
        for f in files:
            p = Path(f.get("path", ""))
            parts = p.parts
            if len(parts) > 1:
                comp_paths.add("/".join(parts[: min(2, len(parts) - 1)]))
            else:
                comp_paths.add("root")

        for cp in sorted(comp_paths):
            components.append(
                self.build_component_brief(cp, files, symbols, dependencies, relationships)
            )

        human_summary = f"""# System Architecture: {full_name}

**Repository Overview:**
- **Files:** {len(files)} source files
- **Symbols:** {len(symbols)} AST symbols extracted
- **Dependencies:** {len(dependencies)} dependency edges
- **Languages:** {', '.join(f'{k}: {v}' for k, v in languages.items())}

## Major Architecture Components ({len(components)})
""" + "\n---\n".join(c.human_summary for c in components)

        llm_context = f"""=== REPOSITORY CURRENT-SYSTEM MODEL ===
REPO: {full_name}
FILES: {len(files)} | SYMBOLS: {len(symbols)} | DEPENDENCIES: {len(dependencies)}
LANGUAGES: {languages}
COMPONENTS ({len(components)}):
""" + "\n".join(f"- {c.name}: {c.symbol_count} symbols, {len(c.dependencies)} deps, {len(c.callers)} callers" for c in components) + "\n======================================="

        return RepositoryBrief(
            repository_id=repository_id,
            full_name=full_name,
            file_count=len(files),
            symbol_count=len(symbols),
            dependency_count=len(dependencies),
            languages=languages,
            components=components,
            human_summary=human_summary,
            llm_context=llm_context,
        )
