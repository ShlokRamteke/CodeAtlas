from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Set


@dataclass
class NormalizedChangeIntent:
    raw_query: str
    action_verbs: List[str] = field(default_factory=list)
    target_files: List[str] = field(default_factory=list)
    target_symbols: List[str] = field(default_factory=list)
    target_components: List[str] = field(default_factory=list)
    intent_summary: str = ""
    is_ambiguous: bool = False


# Known action verbs indicating software modification intent
ACTION_VERBS: Set[str] = {
    "add",
    "alter",
    "change",
    "clean",
    "convert",
    "deprecate",
    "delete",
    "drop",
    "extract",
    "fix",
    "implement",
    "integrate",
    "isolate",
    "migrate",
    "modify",
    "move",
    "optimize",
    "re-architect",
    "rearchitect",
    "refactor",
    "remove",
    "rename",
    "replace",
    "rewrite",
    "split",
    "swap",
    "switch",
    "update",
    "upgrade",
}

# Regex for file paths with extensions
FILE_PATH_PATTERN = re.compile(
    r"\b(?:[\w.-]+/)*[\w.-]+\.(?:ts|tsx|js|jsx|py|go|rs|java|rb|json|yaml|yml|md|sql|toml)\b",
    re.IGNORECASE,
)

# Regex for identifiers: PascalCase, camelCase, snake_case symbols with at least 3 chars
SYMBOL_PATTERN = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b")

# Noise words to filter out of symbol extraction
COMMON_STOPWORDS: Set[str] = {
    "the", "and", "for", "with", "from", "into", "that", "this", "what",
    "when", "where", "which", "how", "why", "does", "will", "would",
    "should", "could", "all", "any", "some", "none", "not", "over",
    "under", "before", "after", "between", "through", "about", "above",
    "below", "other", "another", "such", "than", "then", "very", "more",
    "most", "also", "just", "code", "file", "files", "module", "service",
    "component", "system", "repo", "repository", "backend", "frontend",
    "database", "table", "class", "function", "method", "variable",
    "provider", "integration", "client", "model", "schema", "controller",
}


class IntentNormalizer:
    """Deterministically normalizes proposed change intent into structured targets."""

    @classmethod
    def normalize(
        cls,
        raw_query: str,
        target_path: Optional[str] = None,
        target_symbol: Optional[str] = None,
        known_files: Optional[List[str]] = None,
        known_symbols: Optional[List[str]] = None,
    ) -> NormalizedChangeIntent:
        query = (raw_query or "").strip()
        verbs: List[str] = []
        files: List[str] = []
        symbols: List[str] = []
        components: List[str] = []

        # 1. Explicit inputs take priority
        if target_path:
            clean_path = target_path.strip().lstrip("/")
            if clean_path and clean_path not in files:
                files.append(clean_path)

        if target_symbol:
            clean_sym = target_symbol.strip()
            if clean_sym and clean_sym not in symbols:
                symbols.append(clean_sym)

        # 2. Extract action verbs
        lowered_words = re.findall(r"\b[a-z][a-z-]*[a-z]\b", query.lower())
        for w in lowered_words:
            if w in ACTION_VERBS and w not in verbs:
                verbs.append(w)

        # 3. Extract candidate file paths
        extracted_paths = FILE_PATH_PATTERN.findall(query)
        for p in extracted_paths:
            clean_p = p.strip().lstrip("/")
            if clean_p not in files:
                files.append(clean_p)

        # 4. Resolve candidate symbols against known symbols or heuristically
        extracted_words = SYMBOL_PATTERN.findall(query)
        known_sym_set = set(known_symbols) if known_symbols else set()
        known_file_set = set(known_files) if known_files else set()

        for w in extracted_words:
            w_lower = w.lower()
            if w_lower in COMMON_STOPWORDS or w_lower in ACTION_VERBS:
                continue

            # If matching known symbol directly
            if known_sym_set and w in known_sym_set:
                if w not in symbols:
                    symbols.append(w)
                continue

            # Heuristic for identifier shapes: PascalCase or snake_case with underscores
            is_pascal = bool(re.match(r"^[A-Z][a-zA-Z0-9]+$", w)) and len(w) > 3
            is_snake = "_" in w and not w.startswith("_")

            if (is_pascal or is_snake) and w not in symbols:
                symbols.append(w)

        # 5. Match against known files if query mentions filename without directory
        if known_file_set:
            for kf in known_file_set:
                basename = kf.split("/")[-1]
                if basename.lower() in query.lower() and kf not in files:
                    files.append(kf)

        # 6. Extract component candidates (e.g. directories like "payments", "auth", "history")
        for f in files:
            parts = f.split("/")
            if len(parts) > 1 and parts[0] not in components:
                components.append(parts[0])

        # 7. Ambiguity check
        is_ambiguous = len(files) == 0 and len(symbols) == 0 and len(verbs) == 0

        # 8. Generate concise distilled summary
        verb_phrase = "/".join(verbs) if verbs else "investigate"
        targets_phrase = ", ".join(files + symbols) if (files or symbols) else "unspecified targets"
        summary = f"{verb_phrase.capitalize()} change affecting {targets_phrase}"

        return NormalizedChangeIntent(
            raw_query=query,
            action_verbs=verbs,
            target_files=files,
            target_symbols=symbols,
            target_components=components,
            intent_summary=summary,
            is_ambiguous=is_ambiguous,
        )
