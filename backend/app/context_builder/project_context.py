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
    # Historical and Engineering Context attached directly to entities
    introducing_commit: Optional[str] = None
    introducing_date: Optional[str] = None
    last_modified_commit: Optional[str] = None
    last_modified_date: Optional[str] = None
    change_count: int = 0
    active_authors: List[str] = field(default_factory=list)
    related_adrs: List[str] = field(default_factory=list)


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
    kind: str  # ast_symbol, import_statement, test_binding, file_header, git_commit, pull_request, issue, architecture_decision, design_constraint
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
class ContextHistoricalChange:
    commit_hash: str
    message: str
    author: str
    committed_at: str
    change_type: str = "modified"  # added, modified, deleted, renamed
    files_changed: List[str] = field(default_factory=list)
    is_introducing: bool = False
    pr_number: Optional[int] = None


@dataclass
class ContextPullRequest:
    pr_number: int
    title: str
    state: str  # open, closed, merged
    author: str
    merged_at: Optional[str] = None
    url: Optional[str] = None
    linked_issue_numbers: List[int] = field(default_factory=list)


@dataclass
class ContextIssue:
    issue_number: int
    title: str
    state: str  # open, closed
    author: str
    closed_at: Optional[str] = None
    labels: List[str] = field(default_factory=list)
    url: Optional[str] = None


@dataclass
class ContextDocument:
    id: str
    path: str
    title: str
    doc_type: str  # adr, design_doc, architecture, specification, general
    status: Optional[str] = None  # for ADRs: accepted, deprecated, etc.
    deciders: Optional[str] = None
    summary: Optional[str] = None


@dataclass
class ContextDesignConstraint:
    id: str
    domain: str  # security, architecture, performance, testing, data_integrity
    constraint_text: str
    source_doc_path: str
    priority: str = "MUST"  # MUST, MUST_NOT, SHOULD, RECOMMENDED


@dataclass
class ProjectContext:
    """
    Canonical Unified Project Context.
    Shared as the single source of truth for both Human UI and AI/Agent reasoning.
    Enriched with Current System (AST), Historical Context (Git, PRs, Issues),
    and Engineering Context (Docs, ADRs, Architectural Invariants).
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
    # Phase 3 Canonical Enrichments
    historical_changes: List[ContextHistoricalChange] = field(default_factory=list)
    related_prs: List[ContextPullRequest] = field(default_factory=list)
    related_issues: List[ContextIssue] = field(default_factory=list)
    documents: List[ContextDocument] = field(default_factory=list)
    design_constraints: List[ContextDesignConstraint] = field(default_factory=list)

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

        # File breakdown with provenance
        file_items = []
        for f in file_entities[:10]:
            intro_str = (
                f" [introduced in `{f.introducing_commit[:8]}`]" if f.introducing_commit else ""
            )
            mod_str = f", {f.change_count} revisions" if f.change_count > 0 else ""
            file_items.append(f"- `{f.path}` ({f.language or 'unknown'}){intro_str}{mod_str}")
        files_md = "\n".join(file_items) or "- *No files indexed*"
        if len(file_entities) > 10:
            files_md += f"\n- *... and {len(file_entities) - 10} more files*"

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

        # Historical Changes breakdown
        history_md = (
            "\n".join(
                f"- [`{c.commit_hash[:8]}`] {c.message.splitlines()[0] if c.message else 'No message'} ({c.author}, {c.committed_at[:10]})"
                + (" **[INTRODUCING]**" if c.is_introducing else "")
                for c in self.historical_changes[:8]
            )
            or "- *No historical commits indexed*"
        )
        if len(self.historical_changes) > 8:
            history_md += (
                f"\n- *... and {len(self.historical_changes) - 8} more historical commits*"
            )

        # PRs and Issues breakdown
        prs_md = (
            "\n".join(
                f"- PR #{p.pr_number}: {p.title} ({p.state.upper()} by {p.author})"
                for p in self.related_prs[:5]
            )
            or "- *No linked pull requests*"
        )

        issues_md = (
            "\n".join(
                f"- Issue #{i.issue_number}: {i.title} ({i.state.upper()})"
                for i in self.related_issues[:5]
            )
            or "- *No linked issues*"
        )

        # Engineering Documentation & ADRs
        adrs = [d for d in self.documents if d.doc_type == "adr"]
        docs_md = (
            "\n".join(
                f"- **{d.title}** (`{d.path}`) [{d.status or 'active'}]"
                + (f" &mdash; {d.summary}" if d.summary else "")
                for d in (adrs if adrs else self.documents)[:6]
            )
            or "- *No engineering ADRs or design docs indexed*"
        )

        # Design Constraints breakdown
        constraints_md = (
            "\n".join(
                f"- [{c.domain.upper()}] **{c.priority}**: {c.constraint_text} (`{c.source_doc_path}`)"
                for c in self.design_constraints[:8]
            )
            or "- *No architectural invariants declared*"
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

#### Indexed Files
{files_md}

#### Indexed Symbols
{sym_md}

### 🔗 Relationships ({len(self.relationships)})
#### Outbound Imports & Dependencies
{imports_md}

#### Test Linkages
{tests_md}

#### Calls & Inheritance
{calls_md}

### ⏳ Historical Evolution ({len(self.historical_changes)} commits)
{history_md}

### 🔀 Provenance Traces ({len(self.related_prs)} PRs, {len(self.related_issues)} Issues)
#### Pull Requests
{prs_md}

#### Associated Issues
{issues_md}

### 📐 Engineering Context ({len(self.documents)} Docs, {len(self.design_constraints)} Constraints)
#### Architecture Decision Records & Docs
{docs_md}

#### Architectural Invariants & Constraints
{constraints_md}

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
        history_strs = [
            f"{c.commit_hash[:7]}: {c.message.splitlines()[0][:50] if c.message else ''}"
            for c in self.historical_changes[:5]
        ]
        pr_strs = [f"PR#{p.pr_number}({p.title[:40]})" for p in self.related_prs[:4]]
        issue_strs = [f"Issue#{i.issue_number}({i.title[:40]})" for i in self.related_issues[:4]]
        adr_strs = [f"ADR:{d.title[:40]}[{d.status or 'active'}]" for d in self.documents[:4]]
        constraint_strs = [
            f"[{c.domain[:4].upper()}]{c.priority}:{c.constraint_text[:60]}"
            for c in self.design_constraints[:5]
        ]
        unknown_strs = [f"{u.target}({u.kind})" for u in self.unknowns[:6]]
        evidence_ids = [e.id[:8] for e in self.evidence[:8]]

        return f"""=== UNIFIED PROJECT CONTEXT BRIEFING ===
TARGET: {self.target_name} (type: {self.target_type}, id: {self.target_id})
CONFIDENCE: {self.confidence:.2f} | PROVENANCE: {self.provenance}
FILES ({len(file_entities)}): [{", ".join(f.path for f in file_entities[:8])}]
SYMBOLS ({len(sym_entities)}): [{", ".join(sym_strs)}]
DEPENDENCIES ({len(dep_strs)}): [{", ".join(dep_strs)}]
TEST_COVERAGE: [{", ".join(test_strs) if test_strs else "NONE_DETECTED"}]
RECENT_HISTORY ({len(self.historical_changes)}): [{"; ".join(history_strs) if history_strs else "NONE"}]
LINKED_PRS_ISSUES: [{", ".join(pr_strs + issue_strs) if (pr_strs or issue_strs) else "NONE"}]
ADRS_DOCS ({len(self.documents)}): [{", ".join(adr_strs) if adr_strs else "NONE"}]
DESIGN_CONSTRAINTS ({len(self.design_constraints)}): [{"; ".join(constraint_strs) if constraint_strs else "NONE"}]
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
                    "introducing_commit": e.introducing_commit,
                    "introducing_date": e.introducing_date,
                    "last_modified_commit": e.last_modified_commit,
                    "last_modified_date": e.last_modified_date,
                    "change_count": e.change_count,
                    "active_authors": e.active_authors,
                    "related_adrs": e.related_adrs,
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
            "historical_changes": [
                {
                    "commit_hash": c.commit_hash,
                    "message": c.message,
                    "author": c.author,
                    "committed_at": c.committed_at,
                    "change_type": c.change_type,
                    "files_changed": c.files_changed,
                    "is_introducing": c.is_introducing,
                    "pr_number": c.pr_number,
                }
                for c in self.historical_changes
            ],
            "related_prs": [
                {
                    "pr_number": p.pr_number,
                    "title": p.title,
                    "state": p.state,
                    "author": p.author,
                    "merged_at": p.merged_at,
                    "url": p.url,
                    "linked_issue_numbers": p.linked_issue_numbers,
                }
                for p in self.related_prs
            ],
            "related_issues": [
                {
                    "issue_number": i.issue_number,
                    "title": i.title,
                    "state": i.state,
                    "author": i.author,
                    "closed_at": i.closed_at,
                    "labels": i.labels,
                    "url": i.url,
                }
                for i in self.related_issues
            ],
            "documents": [
                {
                    "id": d.id,
                    "path": d.path,
                    "title": d.title,
                    "doc_type": d.doc_type,
                    "status": d.status,
                    "deciders": d.deciders,
                    "summary": d.summary,
                }
                for d in self.documents
            ],
            "design_constraints": [
                {
                    "id": dc.id,
                    "domain": dc.domain,
                    "constraint_text": dc.constraint_text,
                    "source_doc_path": dc.source_doc_path,
                    "priority": dc.priority,
                }
                for dc in self.design_constraints
            ],
            "human_markdown": self.to_human_markdown(),
            "llm_prompt_context": self.to_llm_prompt(),
        }
