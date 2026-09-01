from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ContextEntity:
    id: str
    name: str
    kind: str  # file, symbol, component
    path: str
    language: Optional[str] = None
    signature: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None


@dataclass
class ContextRelationship:
    source_name: str
    source_path: str
    target_name: str
    target_path: str
    type: str  # imports, calls, extends, implements, tested_by
    confidence: float = 1.0
    resolution_method: str = "tree_sitter_ast"


@dataclass
class ContextEvidence:
    id: str
    source_path: str
    kind: str  # ast_symbol, import_statement, test_binding, file_header
    content: str
    confidence: float = 1.0
    provenance: str = "tree_sitter_ast"


@dataclass
class ContextUnknown:
    kind: str  # untested, unresolved_dependency, missing_signature, empty_file, low_confidence
    target: str
    description: str
    severity: str = "medium"  # low, medium, high


@dataclass
class ProjectContext:
    """
    Canonical Unified Project Context.
    Shared as the single source of truth for both Human UI and AI/Agent reasoning.
    """

    target_type: str  # repository, component, file, symbol
    target_id: str
    target_name: str
    summary: str
    entities: List[ContextEntity] = field(default_factory=list)
    relationships: List[ContextRelationship] = field(default_factory=list)
    evidence: List[ContextEvidence] = field(default_factory=list)
    unknowns: List[ContextUnknown] = field(default_factory=list)
    confidence: float = 1.0
    provenance: str = "tree_sitter_ast"

    def to_human_markdown(self) -> str:
        """Render formatted human-readable markdown briefing."""
        sym_entities = [e for e in self.entities if e.kind == "symbol"]
        file_entities = [e for e in self.entities if e.kind == "file"]

        # Symbol breakdown
        sym_md = (
            "\n".join(
                f"- `{s.signature or s.name}` ({s.path}:{s.line_start}-{s.line_end})"
                for s in sym_entities[:15]
            )
            or "- *No symbols indexed*"
        )
        if len(sym_entities) > 15:
            sym_md += f"\n- *... and {len(sym_entities) - 15} more symbols*"

        # Relationships breakdown
        imports = [r for r in self.relationships if r.type == "imports"]
        tested_by = [r for r in self.relationships if r.type == "tested_by"]
        calls = [r for r in self.relationships if r.type in ["calls", "extends", "implements"]]

        imports_md = (
            "\n".join(
                f"- `{r.source_name}` &rarr; `{r.target_name}` (`{r.target_path}`) [{r.resolution_method}, {int(r.confidence * 100)}% conf]"
                for r in imports[:10]
            )
            or "- *None*"
        )

        tests_md = (
            "\n".join(
                f"- `{r.source_name}` tested by `{r.target_name}` (`{r.target_path}`)"
                for r in tested_by
            )
            or "- *No associated test suite match*"
        )

        calls_md = (
            "\n".join(f"- `{r.source_name}` {r.type} `{r.target_name}`" for r in calls[:10])
            or "- *No caller/inheritance edges*"
        )

        # Unknowns & Gaps
        unknowns_md = (
            "\n".join(
                f"- [{u.severity.upper()}] **{u.target}**: {u.description} (`{u.kind}`)"
                for u in self.unknowns
            )
            or "- *No architectural gaps detected (High confidence)*"
        )

        # Evidence
        evidence_md = (
            "\n".join(
                f"- `[{e.id[:8]}]` {e.kind} in `{e.source_path}` ({int(e.confidence * 100)}% conf)"
                for e in self.evidence[:8]
            )
            or "- *No raw evidence records*"
        )

        return f"""# Project Context: {self.target_name}
**Target Type:** {self.target_type.capitalize()} | **Confidence:** {int(self.confidence * 100)}% | **Provenance:** `{self.provenance}`

{self.summary}

### 📦 Key Entities ({len(self.entities)})
- **Files:** {len(file_entities)}
- **Symbols:** {len(sym_entities)}

{sym_md}

### 🔗 Relationships ({len(self.relationships)})
#### Outbound Imports & Dependencies
{imports_md}

#### Test Linkages
{tests_md}

#### Calls & Inheritance
{calls_md}

### ⚠️ Unknowns & Uncertainties ({len(self.unknowns)})
{unknowns_md}

### 📋 Grounded Evidence Records ({len(self.evidence)})
{evidence_md}
"""

    def to_llm_prompt(self) -> str:
        """Render compact, token-efficient serialization for LLM reasoning prompt injection."""
        sym_entities = [e for e in self.entities if e.kind == "symbol"]
        file_entities = [e for e in self.entities if e.kind == "file"]

        sym_strs = [f"{s.name}({s.signature or s.name})" for s in sym_entities[:15]]
        dep_strs = [
            f"{r.source_name}->{r.target_name}" for r in self.relationships if r.type == "imports"
        ][:12]
        test_strs = [
            f"{r.source_name}:{r.target_path}" for r in self.relationships if r.type == "tested_by"
        ]
        unknown_strs = [f"{u.target}({u.kind})" for u in self.unknowns[:8]]
        evidence_ids = [e.id[:8] for e in self.evidence[:10]]

        return f"""=== UNIFIED PROJECT CONTEXT BRIEFING ===
TARGET: {self.target_name} (type: {self.target_type}, id: {self.target_id})
CONFIDENCE: {self.confidence:.2f} | PROVENANCE: {self.provenance}
FILES ({len(file_entities)}): [{", ".join(f.path for f in file_entities[:8])}]
SYMBOLS ({len(sym_entities)}): [{", ".join(sym_strs)}]
DEPENDENCIES ({len(dep_strs)}): [{", ".join(dep_strs)}]
TEST_COVERAGE: [{", ".join(test_strs) if test_strs else "NONE_DETECTED"}]
UNKNOWNS_GAPS ({len(self.unknowns)}): [{", ".join(unknown_strs) if unknown_strs else "NONE"}]
EVIDENCE_RECORDS ({len(self.evidence)}): [{", ".join(evidence_ids)}]
========================================"""

    def to_dict(self) -> Dict[str, Any]:
        """Structured dictionary for REST API serialization."""
        return {
            "target_type": self.target_type,
            "target_id": self.target_id,
            "target_name": self.target_name,
            "summary": self.summary,
            "confidence": self.confidence,
            "provenance": self.provenance,
            "entities": [
                {
                    "id": e.id,
                    "name": e.name,
                    "kind": e.kind,
                    "path": e.path,
                    "language": e.language,
                    "signature": e.signature,
                    "line_start": e.line_start,
                    "line_end": e.line_end,
                }
                for e in self.entities
            ],
            "relationships": [
                {
                    "source_name": r.source_name,
                    "source_path": r.source_path,
                    "target_name": r.target_name,
                    "target_path": r.target_path,
                    "type": r.type,
                    "confidence": r.confidence,
                    "resolution_method": r.resolution_method,
                }
                for r in self.relationships
            ],
            "evidence": [
                {
                    "id": e.id,
                    "source_path": e.source_path,
                    "kind": e.kind,
                    "content": e.content,
                    "confidence": e.confidence,
                    "provenance": e.provenance,
                }
                for e in self.evidence
            ],
            "unknowns": [
                {
                    "kind": u.kind,
                    "target": u.target,
                    "description": u.description,
                    "severity": u.severity,
                }
                for u in self.unknowns
            ],
            "human_markdown": self.to_human_markdown(),
            "llm_prompt_context": self.to_llm_prompt(),
        }
