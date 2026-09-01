from __future__ import annotations

import hashlib
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dependency import CodeDependency, DependencyKind
from app.models.repository import Repository, RepositoryStatus
from app.models.source_file import SourceFile
from app.models.symbol import Symbol, SymbolKind
from app.parser.ast_parser import ASTCodeParser, ParsedFileResult
from app.parser.relationship_analyzer import ArchitectureGraph, RelationshipAnalyzer

# Ignore common build and binary directories
IGNORED_DIRS = {
    ".git",
    "node_modules",
    ".next",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".idea",
    ".vscode",
    "coverage",
}

# Supported source, configuration, and documentation extensions
SUPPORTED_EXTENSIONS = {
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".py",
    ".pyw",
    ".pyi",
    ".json",
    ".jsonc",
    ".json5",
    ".md",
    ".markdown",
    ".mdx",
    ".yml",
    ".yaml",
    ".toml",
    ".sh",
    ".bash",
    ".zsh",
    ".sql",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".go",
    ".rs",
    ".java",
    ".c",
    ".h",
    ".cpp",
    ".cc",
    ".cxx",
    ".hpp",
    ".rb",
    ".php",
    ".proto",
    ".graphql",
    ".gql",
    ".txt",
    ".dockerfile",
}


# Regex secret scan patterns
SECRET_PATTERNS = [
    re.compile(r"(?i)(?:api_key|apikey|secret_key|private_key|token|password)\s*[:=]\s*['\"]([a-zA-Z0-9_\-\.]{16,})['\"]"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"ghp_[0-9a-zA-Z]{36}"),
    re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,48}"),
]


def redact_secrets(code: str) -> str:
    """Secret-scan and redact potential credentials before storage."""
    sanitized = code
    for pattern in SECRET_PATTERNS:
        sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
    return sanitized


class IngestionEngine:
    """Deterministic repository ingestion and symbol indexing engine."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.parser = ASTCodeParser()
        self.analyzer = RelationshipAnalyzer()

    @staticmethod
    def compute_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    async def ingest_directory(
        self,
        repository_id: uuid.UUID,
        root_dir: str | Path,
    ) -> ArchitectureGraph:
        """Ingest all supported source files from a local directory or checkout."""
        root_path = Path(root_dir)
        file_map: Dict[str, str] = {}

        for dirpath, dirnames, filenames in os.walk(root_path):
            # Prune ignored directories
            dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS and not d.startswith(".")]

            for fname in filenames:
                ext = Path(fname).suffix.lower()
                if ext in SUPPORTED_EXTENSIONS:
                    full_p = Path(dirpath) / fname
                    rel_p = str(full_p.relative_to(root_path))
                    try:
                        with open(full_p, encoding="utf-8", errors="ignore") as f:
                            file_map[rel_p] = f.read()
                    except Exception:
                        continue

        return await self.ingest_files(repository_id, file_map)

    async def ingest_files(
        self,
        repository_id: uuid.UUID,
        files: Dict[str, str],
    ) -> ArchitectureGraph:
        """Ingest a map of {relative_path: file_content} into the repository database."""
        # 1. Fetch Repository
        stmt = select(Repository).where(Repository.id == repository_id)
        result = await self.session.execute(stmt)
        repo = result.scalar_one_or_none()
        if not repo:
            raise ValueError(f"Repository {repository_id} not found")

        repo.status = RepositoryStatus.INDEXING
        await self.session.flush()

        # 2. Parse all files with Tree-sitter
        parsed_results: List[ParsedFileResult] = []
        for path, raw_content in files.items():
            sanitized_content = redact_secrets(raw_content)
            parsed = self.parser.parse_code(path, sanitized_content)
            parsed_results.append(parsed)

        # 3. Clean existing indexed files and symbols for complete sync
        await self.session.execute(
            delete(CodeDependency).where(CodeDependency.repository_id == repository_id)
        )
        await self.session.execute(
            delete(Symbol).where(Symbol.repository_id == repository_id)
        )
        await self.session.execute(
            delete(SourceFile).where(SourceFile.repository_id == repository_id)
        )

        # 4. Insert new SourceFiles, Symbols, and Dependencies
        total_symbols = 0
        for parsed in parsed_results:
            raw_content = files[parsed.path]
            content_hash = self.compute_hash(raw_content)

            source_file = SourceFile(
                id=uuid.uuid4(),
                repository_id=repository_id,
                path=parsed.path,
                language=parsed.language,
                content_hash=content_hash,
                size_bytes=len(raw_content.encode("utf-8")),
                summary=f"{parsed.language.capitalize()} module with {len(parsed.symbols)} symbols",
            )
            self.session.add(source_file)
            await self.session.flush()

            # Add symbols
            for sym in parsed.symbols:
                kind_val = SymbolKind.FUNCTION
                try:
                    kind_val = SymbolKind(sym.kind)
                except ValueError:
                    kind_val = SymbolKind.FUNCTION

                symbol_record = Symbol(
                    id=uuid.uuid4(),
                    file_id=source_file.id,
                    repository_id=repository_id,
                    name=sym.name,
                    kind=kind_val,
                    line_start=sym.line_start,
                    line_end=sym.line_end,
                    signature=sym.signature,
                    docstring=sym.docstring,
                )
                self.session.add(symbol_record)
                total_symbols += 1

            # Add dependencies
            for dep in parsed.dependencies:
                dep_kind = DependencyKind.INTERNAL
                if dep.kind == "external":
                    dep_kind = DependencyKind.EXTERNAL
                elif dep.kind == "relative":
                    dep_kind = DependencyKind.RELATIVE

                dep_record = CodeDependency(
                    id=uuid.uuid4(),
                    repository_id=repository_id,
                    source_file_id=source_file.id,
                    source_path=parsed.path,
                    target_path=dep.target_path,
                    imported_symbol=dep.imported_symbol,
                    kind=dep_kind,
                )
                self.session.add(dep_record)

        # 5. Compute Architecture Graph
        arch_graph = self.analyzer.analyze_repository(parsed_results)

        # 6. Update Repository stats
        repo.file_count = len(files)
        repo.symbol_count = total_symbols
        repo.status = RepositoryStatus.READY
        repo.indexed_at = datetime.now(timezone.utc)
        await self.session.commit()

        return arch_graph
