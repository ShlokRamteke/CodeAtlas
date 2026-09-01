from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import tree_sitter_javascript
import tree_sitter_python
import tree_sitter_typescript
from tree_sitter import Language, Node, Parser


@dataclass
class ExtractedSymbol:
    name: str
    kind: str  # function, class, interface, type, method, variable, constant
    line_start: int
    line_end: int
    signature: Optional[str] = None
    docstring: Optional[str] = None


@dataclass
class ExtractedDependency:
    target_path: str
    imported_symbol: Optional[str] = None
    kind: str = "internal"  # internal, external, relative
    confidence: float = 1.0
    resolution_method: str = "tree_sitter_ast"



@dataclass
class ParsedFileResult:
    path: str
    language: str
    symbols: List[ExtractedSymbol] = field(default_factory=list)
    dependencies: List[ExtractedDependency] = field(default_factory=list)
    summary: Optional[str] = None


FILENAME_LANGUAGE_MAP: dict[str, str] = {
    "dockerfile": "dockerfile",
    "makefile": "makefile",
    "gnumakefile": "makefile",
    "cmakelists.txt": "cmake",
    "gemfile": "ruby",
    "rakefile": "ruby",
    "procfile": "yaml",
}

EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    # TypeScript / JavaScript
    ".ts": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    # Python
    ".py": "python",
    ".pyw": "python",
    ".pyi": "python",
    # Config & Markup
    ".yml": "yaml",
    ".yaml": "yaml",
    ".json": "json",
    ".jsonc": "json",
    ".json5": "json",
    ".md": "markdown",
    ".markdown": "markdown",
    ".mdx": "markdown",
    ".toml": "toml",
    ".xml": "xml",
    ".svg": "svg",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "css",
    ".sass": "css",
    ".less": "css",
    # Systems / Backends
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".sql": "sql",
    ".rb": "ruby",
    ".php": "php",
    ".proto": "protobuf",
    ".graphql": "graphql",
    ".gql": "graphql",
    ".txt": "text",
    ".dockerfile": "dockerfile",
}


class ASTCodeParser:
    """Multi-language AST Parser using Tree-sitter for deterministic code understanding."""

    def __init__(self) -> None:
        self.ts_lang = Language(tree_sitter_typescript.language_typescript())
        self.tsx_lang = Language(tree_sitter_typescript.language_tsx())
        self.js_lang = Language(tree_sitter_javascript.language())
        self.py_lang = Language(tree_sitter_python.language())

    @staticmethod
    def detect_language(file_path: str) -> str:
        name = Path(file_path).name.lower()
        if name in FILENAME_LANGUAGE_MAP:
            return FILENAME_LANGUAGE_MAP[name]
        if name.startswith("dockerfile."):
            return "dockerfile"
        if name.startswith(".env"):
            return "config"

        ext = Path(file_path).suffix.lower()
        return EXTENSION_LANGUAGE_MAP.get(ext, "unknown")

    def _get_parser_for_path(self, file_path: str) -> tuple[Optional[Parser], str]:
        lang = self.detect_language(file_path)
        if lang == "typescript":
            return Parser(self.ts_lang), "typescript"
        if lang == "tsx":
            return Parser(self.tsx_lang), "tsx"
        if lang == "javascript":
            return Parser(self.js_lang), "javascript"
        if lang == "python":
            return Parser(self.py_lang), "python"
        return None, lang


    def parse_code(self, file_path: str, code: str) -> ParsedFileResult:
        parser, lang = self._get_parser_for_path(file_path)
        if not parser or not code.strip():
            return ParsedFileResult(path=file_path, language=lang)

        tree = parser.parse(code.encode("utf-8"))
        root_node = tree.root_node

        symbols: List[ExtractedSymbol] = []
        dependencies: List[ExtractedDependency] = []

        if lang in ["typescript", "tsx", "javascript"]:
            self._extract_js_ts(root_node, code, symbols, dependencies)
        elif lang == "python":
            self._extract_python(root_node, code, symbols, dependencies)

        return ParsedFileResult(
            path=file_path,
            language=lang,
            symbols=symbols,
            dependencies=dependencies,
        )

    def _extract_js_ts(
        self,
        root_node: Node,
        code: str,
        symbols: List[ExtractedSymbol],
        dependencies: List[ExtractedDependency],
    ) -> None:
        code_bytes = code.encode("utf-8")

        def get_text(n: Node) -> str:
            return code_bytes[n.start_byte : n.end_byte].decode("utf-8")

        def visit(node: Node) -> None:
            # 1. Imports
            if node.type == "import_statement":
                source_node = node.child_by_field_name("source")
                if source_node:
                    target = get_text(source_node).strip("'\"`")
                    if target.startswith("."):
                        kind = "relative"
                    elif (
                        target.startswith("@/")
                        or target.startswith("~/")
                        or target.startswith("#/")
                        or target.startswith("$lib/")
                        or target.startswith("src/")
                        or target.startswith("app/")
                        or target.startswith("components/")
                        or target.startswith("lib/")
                    ):
                        kind = "internal"
                    else:
                        kind = "external"


                    clause_node = node.child_by_field_name("clause") or node.child_by_field_name("import")
                    if not clause_node:
                        for child in node.children:
                            if child.type in ["import_clause", "named_imports"]:
                                clause_node = child
                                break

                    imported_symbols: List[str] = []
                    if clause_node:
                        for child in clause_node.named_children:
                            if child.type in ["identifier", "type_identifier"]:
                                imported_symbols.append(get_text(child))
                            elif child.type == "named_imports":
                                for spec in child.named_children:
                                    if spec.type in ["import_specifier", "type_import_specifier"]:
                                        name_node = spec.child_by_field_name("name") or (
                                            spec.named_children[0] if spec.named_children else None
                                        )
                                        if name_node:
                                            imported_symbols.append(get_text(name_node))

                    if imported_symbols:
                        for sym in imported_symbols:
                            dependencies.append(ExtractedDependency(target_path=target, imported_symbol=sym, kind=kind))
                    else:
                        dependencies.append(ExtractedDependency(target_path=target, kind=kind))

            # 2. Functions
            elif node.type in ["function_declaration", "generator_function_declaration"]:
                name_node = node.child_by_field_name("name")
                if not name_node:
                    for child in node.named_children:
                        if child.type in ["identifier", "property_identifier"]:
                            name_node = child
                            break
                if name_node:
                    name = get_text(name_node)
                    first_line = code[node.start_byte : node.end_byte].split("\n")[0].strip()
                    symbols.append(
                        ExtractedSymbol(
                            name=name,
                            kind="function",
                            line_start=node.start_point[0] + 1,
                            line_end=node.end_point[0] + 1,
                            signature=first_line[:200],
                        )
                    )

            # 3. Classes
            elif node.type in ["class_declaration", "abstract_class_declaration"]:
                name_node = node.child_by_field_name("name")
                if not name_node:
                    for child in node.named_children:
                        if child.type in ["identifier", "type_identifier"]:
                            name_node = child
                            break
                if name_node:
                    name = get_text(name_node)
                    first_line = code[node.start_byte : node.end_byte].split("\n")[0].strip()
                    symbols.append(
                        ExtractedSymbol(
                            name=name,
                            kind="class",
                            line_start=node.start_point[0] + 1,
                            line_end=node.end_point[0] + 1,
                            signature=first_line[:200],
                        )
                    )

            # 4. Interfaces
            elif node.type == "interface_declaration":
                name_node = node.child_by_field_name("name")
                if not name_node:
                    for child in node.named_children:
                        if child.type in ["identifier", "type_identifier"]:
                            name_node = child
                            break
                if name_node:
                    name = get_text(name_node)
                    symbols.append(
                        ExtractedSymbol(
                            name=name,
                            kind="interface",
                            line_start=node.start_point[0] + 1,
                            line_end=node.end_point[0] + 1,
                            signature=f"interface {name}",
                        )
                    )

            # 5. Type Aliases
            elif node.type == "type_alias_declaration":
                name_node = node.child_by_field_name("name")
                if not name_node:
                    for child in node.named_children:
                        if child.type in ["identifier", "type_identifier"]:
                            name_node = child
                            break
                if name_node:
                    name = get_text(name_node)
                    symbols.append(
                        ExtractedSymbol(
                            name=name,
                            kind="type",
                            line_start=node.start_point[0] + 1,
                            line_end=node.end_point[0] + 1,
                            signature=f"type {name}",
                        )
                    )

            # 6. Methods
            elif node.type == "method_definition":
                name_node = node.child_by_field_name("name")
                if not name_node:
                    for child in node.named_children:
                        if child.type in ["identifier", "property_identifier"]:
                            name_node = child
                            break
                if name_node:
                    name = get_text(name_node)
                    first_line = code[node.start_byte : node.end_byte].split("\n")[0].strip()
                    symbols.append(
                        ExtractedSymbol(
                            name=name,
                            kind="method",
                            line_start=node.start_point[0] + 1,
                            line_end=node.end_point[0] + 1,
                            signature=first_line[:200],
                        )
                    )

            # 7. Lexical Declarations (const x = () => ..., const MY_CONFIG = ...)
            elif node.type == "lexical_declaration":
                for declarator in node.named_children:
                    if declarator.type == "variable_declarator":
                        name_node = declarator.child_by_field_name("name")
                        if not name_node:
                            for child in declarator.named_children:
                                if child.type in ["identifier", "property_identifier"]:
                                    name_node = child
                                    break
                        value_node = declarator.child_by_field_name("value")
                        if not value_node and len(declarator.named_children) > 1:
                            value_node = declarator.named_children[1]

                        if name_node:
                            name = get_text(name_node)
                            kind = "variable"
                            if value_node and value_node.type in ["arrow_function", "function"]:
                                kind = "function"
                            elif name.isupper():
                                kind = "constant"

                            first_line = code[declarator.start_byte : declarator.end_byte].split("\n")[0].strip()
                            symbols.append(
                                ExtractedSymbol(
                                    name=name,
                                    kind=kind,
                                    line_start=declarator.start_point[0] + 1,
                                    line_end=declarator.end_point[0] + 1,
                                    signature=first_line[:200],
                                )
                            )

            for child in node.children:
                visit(child)

        visit(root_node)

    def _extract_python(
        self,
        root_node: Node,
        code: str,
        symbols: List[ExtractedSymbol],
        dependencies: List[ExtractedDependency],
    ) -> None:
        code_bytes = code.encode("utf-8")

        def get_text(n: Node) -> str:
            return code_bytes[n.start_byte : n.end_byte].decode("utf-8")

        def visit(node: Node) -> None:
            if node.type == "import_statement":
                for child in node.named_children:
                    if child.type == "dotted_name":
                        pkg = get_text(child)
                        dependencies.append(
                            ExtractedDependency(
                                target_path=pkg, kind="external" if "." not in pkg else "internal"
                            )
                        )

            elif node.type == "import_from_statement":
                module_node = node.child_by_field_name("module_name")
                module_name = ""
                if module_node:
                    module_name = get_text(module_node)

                for child in node.named_children:
                    if child.type == "dotted_name" and child != module_node:
                        imported = get_text(child)
                        dependencies.append(
                            ExtractedDependency(
                                target_path=module_name,
                                imported_symbol=imported,
                                kind="relative" if module_name.startswith(".") else "internal",
                            )
                        )

            elif node.type in ["function_definition", "async_function_definition"]:
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = get_text(name_node)
                    first_line = code[node.start_byte : node.end_byte].split("\n")[0].strip()

                    docstring = None
                    body = node.child_by_field_name("body")
                    if body and body.named_children and body.named_children[0].type == "expression_statement":
                        expr = body.named_children[0].named_children[0]
                        if expr.type == "string":
                            docstring = get_text(expr).strip("'\" \n")

                    symbols.append(
                        ExtractedSymbol(
                            name=name,
                            kind="function",
                            line_start=node.start_point[0] + 1,
                            line_end=node.end_point[0] + 1,
                            signature=first_line[:200],
                            docstring=docstring,
                        )
                    )

            elif node.type == "class_definition":
                name_node = node.child_by_field_name("name")
                if name_node:
                    name = get_text(name_node)
                    first_line = code[node.start_byte : node.end_byte].split("\n")[0].strip()

                    docstring = None
                    body = node.child_by_field_name("body")
                    if body and body.named_children and body.named_children[0].type == "expression_statement":
                        expr = body.named_children[0].named_children[0]
                        if expr.type == "string":
                            docstring = get_text(expr).strip("'\" \n")

                    symbols.append(
                        ExtractedSymbol(
                            name=name,
                            kind="class",
                            line_start=node.start_point[0] + 1,
                            line_end=node.end_point[0] + 1,
                            signature=first_line[:200],
                            docstring=docstring,
                        )
                    )

            for child in node.children:
                visit(child)

        visit(root_node)
