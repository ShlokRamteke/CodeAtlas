from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def estimate_tokens(text: str) -> int:
    """Fast, calibrated token estimation heuristic for code and English prose.

    Standard OpenAI/Anthropic tokenizers average ~3.8-4.0 characters per token
    for mixed text/code, with word/delimiter boundaries adding slight overhead.
    """
    if not text:
        return 0
    # Base character count heuristic (~3.8 chars/token)
    char_tokens = len(text) / 3.8
    # Word count heuristic (~1.3 tokens/word)
    words = len(re.findall(r"\w+|[^\w\s]", text))
    word_tokens = words * 1.15
    # Weighted blend
    estimated = int(math.ceil(0.6 * char_tokens + 0.4 * word_tokens))
    return max(1, estimated)


def estimate_json_tokens(data: Any) -> int:
    """Estimate token consumption of serialized JSON data."""
    if data is None:
        return 0
    serialized = json.dumps(data, separators=(",", ":"))
    return estimate_tokens(serialized)


@dataclass
class OmissionMarker:
    """Recoverable omission token pointing to an unshed detail record."""

    ref_id: str  # e.g., "ref#ev-12345678", "ref#inv-perf-01", "ref#commit-c89a01"
    marker_type: str  # "evidence", "commit", "invariant", "blast_node", "test", "doc"
    title: str
    summary: str
    original_payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ref_id": self.ref_id,
            "marker_type": self.marker_type,
            "title": self.title,
            "summary": self.summary,
            "original_payload": self.original_payload,
        }

    def to_dense_json(self) -> Dict[str, Any]:
        return {
            "_omitted": True,
            "ref": self.ref_id,
            "type": self.marker_type,
            "title": self.title,
            "summary": self.summary,
        }

    def to_markdown_tag(self) -> str:
        return f"`[{self.ref_id}]` *({self.title})*"


class OmissionRegistry:
    """Registry maintaining shed items allowing on-demand retrieval by reference ID."""

    def __init__(self) -> None:
        self._registry: Dict[str, OmissionMarker] = {}

    def register(
        self,
        ref_id: str,
        marker_type: str,
        title: str,
        summary: str,
        original_payload: Optional[Dict[str, Any]] = None,
    ) -> OmissionMarker:
        marker = OmissionMarker(
            ref_id=ref_id,
            marker_type=marker_type,
            title=title,
            summary=summary,
            original_payload=original_payload or {},
        )
        self._registry[ref_id] = marker
        return marker

    def get(self, ref_id: str) -> Optional[OmissionMarker]:
        return self._registry.get(ref_id)

    def all_markers(self) -> List[OmissionMarker]:
        return list(self._registry.values())

    def clear(self) -> None:
        self._registry.clear()


# Global in-memory registry for session lookups
GLOBAL_OMISSION_REGISTRY = OmissionRegistry()


@dataclass
class DistilledResult:
    """Result of token-budgeted distillation with dual projections and telemetry."""

    content_text: str  # Human Markdown or JSON string
    content_json: Optional[Dict[str, Any]]  # Parsed dense JSON if requested format is JSON
    format: str  # "markdown" or "json"
    token_budget: Optional[int]
    estimated_tokens: int
    is_distilled: bool
    omitted_count: int
    omissions: List[OmissionMarker]
    shed_tier: int  # 0 = unconstrained/no shedding, 1..5 = tier reached


class TokenBudgetDistiller:
    """Deterministic token budgeting and priority shedding distiller.

    Shedding Tiers:
    - Tier 0: Unbudgeted / fits under budget. Full fidelity.
    - Tier 1: Shed verbose raw evidence snippets and deep commit histories.
    - Tier 2: Shed transitive blast radius leaf nodes and lower-confidence co-change partners.
    - Tier 3: Shed secondary AST relationships and non-priority guarding tests (retain top reach-ranked).
    - Tier 4: Shed non-governing/superseded invariant rationales and doc body sections (retain statements).
    - Tier 5: Retain strictly core targets, quantitative change risk, primary warning alerts, and omission index.
    """

    @classmethod
    def distill_brief(
        cls,
        brief_data: Dict[str, Any],
        token_budget: Optional[int] = None,
        output_format: str = "markdown",
        registry: Optional[OmissionRegistry] = None,
    ) -> DistilledResult:
        """Distill a Pre-Change Investigation Brief into either Human Markdown or Dense Agent JSON."""
        reg = registry or GLOBAL_OMISSION_REGISTRY

        # Attempt full rendering first
        if output_format == "json":
            raw_data = cls._build_dense_agent_json(brief_data, shed_tier=0, registry=reg)
            raw_text = json.dumps(raw_data, indent=2)
            est_tokens = estimate_tokens(raw_text)
        else:
            raw_text = cls._build_human_markdown(brief_data, shed_tier=0, registry=reg)
            raw_data = None
            est_tokens = estimate_tokens(raw_text)

        # If no budget specified or fits in budget, return tier 0
        if token_budget is None or est_tokens <= token_budget:
            return DistilledResult(
                content_text=raw_text,
                content_json=raw_data,
                format=output_format,
                token_budget=token_budget,
                estimated_tokens=est_tokens,
                is_distilled=False,
                omitted_count=0,
                omissions=[],
                shed_tier=0,
            )

        # Sequentially apply shedding tiers 1 through 5 until within budget
        omissions_before = len(reg.all_markers())
        chosen_tier = 0
        final_text = raw_text
        final_json = raw_data
        final_tokens = est_tokens

        for tier in range(1, 6):
            if output_format == "json":
                candidate_json = cls._build_dense_agent_json(
                    brief_data, shed_tier=tier, registry=reg
                )
                candidate_text = json.dumps(candidate_json, indent=2)
                candidate_tokens = estimate_tokens(candidate_text)
                final_json = candidate_json
                final_text = candidate_text
            else:
                candidate_text = cls._build_human_markdown(brief_data, shed_tier=tier, registry=reg)
                candidate_tokens = estimate_tokens(candidate_text)
                final_text = candidate_text
                final_json = None

            final_tokens = candidate_tokens
            chosen_tier = tier

            if candidate_tokens <= token_budget:
                break

        current_omissions = reg.all_markers()[omissions_before:]

        return DistilledResult(
            content_text=final_text,
            content_json=final_json,
            format=output_format,
            token_budget=token_budget,
            estimated_tokens=final_tokens,
            is_distilled=True,
            omitted_count=len(current_omissions),
            omissions=current_omissions,
            shed_tier=chosen_tier,
        )

    @classmethod
    def _build_human_markdown(
        cls,
        brief: Dict[str, Any],
        shed_tier: int,
        registry: OmissionRegistry,
    ) -> str:
        """Render human-facing markdown with priority shedding."""
        target_files = brief.get("target_files", [])
        target_symbols = brief.get("target_symbols", [])
        signals = brief.get("signals", {})
        claims = brief.get("claims", [])
        constraints = brief.get("constraints", [])
        unknowns = brief.get("unknowns", [])
        recommended_checks = brief.get("recommended_checks", [])
        evidence = brief.get("evidence", [])

        # Quantitative Risk Header
        risk_sig = signals.get("change_risk", {})
        risk_score = risk_sig.get("risk_score", 0.0)
        risk_level = risk_sig.get("risk_level", "LOW")
        km = risk_sig.get("kamei_metrics", {})
        entropy = km.get("shannon_entropy", risk_sig.get("shannon_entropy", 0.0))
        defect_pressure = risk_sig.get("defect_pressure", 0.0)

        sections = []
        sections.append(
            f"# Pre-Change Investigation Brief: {brief.get('intent_summary', 'Change Proposal')}"
        )
        sections.append(
            f"**Risk Level:** `{risk_level}` (Score: {risk_score:.2f}) | "
            f"**Entropy:** `{entropy:.2f}` | "
            f"**Defect Pressure:** `{defect_pressure:.2f}`"
        )

        if shed_tier > 0:
            sections.append(
                f"> [!NOTE]\n"
                f"> Distilled with Priority Shedding (Tier {shed_tier}). "
                f"Shed elements can be expanded via `[ref#<id>]` tokens."
            )

        # Targets
        t_files = ", ".join(f"`{f}`" for f in target_files) if target_files else "*None specified*"
        t_syms = (
            ", ".join(f"`{s}`" for s in target_symbols) if target_symbols else "*None specified*"
        )
        sections.append(f"### 🎯 Targets\n- **Files:** {t_files}\n- **Symbols:** {t_syms}")

        # Primary Warnings & Recommended Checks (Tier 5 - Never shed)
        if recommended_checks:
            checks_md = "\n".join(
                f"- [ ] {c}"
                for c in (recommended_checks if shed_tier < 4 else recommended_checks[:3])
            )
            sections.append(f"### 🛡️ Pre-Implementation Checklist\n{checks_md}")

        # Proposed Code Changes & Implementation Blueprint (Tier 5 - retained)
        code_changes = brief.get("code_changes", [])
        if code_changes:
            change_lines = []
            selected_changes = code_changes if shed_tier < 4 else code_changes[:3]
            for ch in selected_changes:
                action = (ch.get("action") or "modify").upper()
                file_path = ch.get("file_path", "unknown")
                symbol_name = ch.get("symbol_name")
                desc = ch.get("description", "")
                snippet = ch.get("signature_or_snippet")
                callers = ch.get("affected_callers", [])

                sym_str = f" &rarr; `{symbol_name}`" if symbol_name else ""
                change_lines.append(f"- **`[{action}]`** `{file_path}`{sym_str}: {desc}")
                if snippet:
                    clean_snippet = snippet.strip()
                    change_lines.append(f"  ```\n  {clean_snippet}\n  ```")
                if callers:
                    caller_str = ", ".join(f"`{c}`" for c in callers[:4])
                    change_lines.append(f"  *Affected Callers:* {caller_str}")

            if shed_tier >= 4 and len(code_changes) > 3:
                marker = registry.register(
                    ref_id="ref#code-changes-remaining",
                    marker_type="code_change",
                    title=f"{len(code_changes) - 3} Additional Code Modifications",
                    summary="Additional code modifications shed for budget",
                    original_payload={"code_changes": code_changes[3:]},
                )
                change_lines.append(f"- *... and {marker.to_markdown_tag()}*")

            sections.append(
                "### 💻 Implementation Blueprint & Code Changes\n" + "\n".join(change_lines)
            )

        # Concurrent In-Flight PRs & Merge Conflicts (Tier 5 - retained)
        overlap_sig = signals.get("concurrent_overlaps", {})
        overlapping_prs = overlap_sig.get("overlapping_prs", [])
        if overlapping_prs:
            ov_lines = []
            if overlap_sig.get("has_direct_conflicts"):
                ov_lines.append(
                    f"> 🚨 **MERGE CONFLICT RISK:** {overlap_sig.get('highest_risk_level')} priority collision with open PR(s)."
                )
            elif overlap_sig.get("has_blast_conflicts"):
                ov_lines.append(
                    "> ⚠️ **DEPENDENCY OVERLAP:** Open PR(s) modify files in direct blast radius."
                )

            for pr_ov in overlapping_prs if shed_tier < 4 else overlapping_prs[:2]:
                pr_num = pr_ov.get("pr_number")
                title = pr_ov.get("pr_title", "")
                author = pr_ov.get("pr_author", "")
                risk = pr_ov.get("risk_level", "HIGH")
                branch = pr_ov.get("head_branch") or "branch"
                files = ", ".join(f"`{f}`" for f in pr_ov.get("overlapping_files", []))
                ov_lines.append(
                    f"- **PR #{pr_num}** by @{author} (`{branch}`) [{risk}]: {title}\n"
                    f"  - Overlapping: {files}\n"
                    f"  - *{pr_ov.get('recommendation', '')}*"
                )

            sections.append("### ⚠️ Concurrent In-Flight Changes\n" + "\n".join(ov_lines))

        # Guarding Tests Section (Tier 3 priority shedding)
        guarding_sig = signals.get("guarding_tests", {})
        ranked_tests = guarding_sig.get("ranked_tests", [])
        untested_files = guarding_sig.get("untested_files", [])
        stale_tests = guarding_sig.get("stale_test_candidates", [])

        if ranked_tests or untested_files or stale_tests:
            test_lines = []
            if untested_files:
                test_lines.append(
                    f"> ⚠️ **Untested Targets:** {', '.join(f'`{f}`' for f in untested_files)}"
                )

            if shed_tier >= 3:
                # Retain top 2 reach-ranked tests, shed the rest
                for t in ranked_tests[:2]:
                    test_lines.append(
                        f"- `#{t.get('test_file')}` (Reach: {t.get('reached_target_count')})"
                    )
                for t in ranked_tests[2:]:
                    test_id = abs(hash(t.get("test_file"))) % 1000000
                    marker = registry.register(
                        ref_id=f"ref#test-{test_id:06d}",
                        marker_type="test",
                        title=f"Test: {t.get('test_file')}",
                        summary=f"Reaches {t.get('reached_target_count')} targets: {', '.join(t.get('reached_targets', []))}",
                        original_payload=t,
                    )
                    test_lines.append(f"- {marker.to_markdown_tag()}")
            else:
                for t in ranked_tests:
                    test_lines.append(
                        f"- `{t.get('test_file')}` &mdash; Guards {t.get('reached_target_count')} file(s)"
                    )

            sections.append("### 🧪 Guarding Tests\n" + "\n".join(test_lines))

        # Blast Radius (Tier 2 priority shedding)
        blast_sig = signals.get("blast_radius", {})
        affected_comps = blast_sig.get("affected_components", [])
        transitive_files = blast_sig.get("transitive_files", [])
        upstream = blast_sig.get("upstream_callers", [])

        if affected_comps or transitive_files or upstream:
            blast_lines = []
            if affected_comps:
                blast_lines.append(
                    f"- **Affected Components:** {', '.join(f'`{c}`' for c in affected_comps)}"
                )

            if shed_tier >= 2:
                # Keep direct callers count, shed individual nodes
                if upstream:
                    marker = registry.register(
                        ref_id="ref#blast-upstream",
                        marker_type="blast_node",
                        title=f"{len(upstream)} Upstream Callers",
                        summary=f"Upstream callers across {len(transitive_files)} transitive files",
                        original_payload={"upstream": upstream, "transitive": transitive_files},
                    )
                    blast_lines.append(
                        f"- **Direct/Transitive Callers:** {len(upstream)} callers shed &rarr; {marker.to_markdown_tag()}"
                    )
            else:
                for u in upstream[:5]:
                    blast_lines.append(f"- Caller: `{u.get('path')}` (Depth {u.get('depth')})")
                if len(upstream) > 5:
                    blast_lines.append(f"- *... and {len(upstream) - 5} more callers*")

            sections.append("### 💥 Blast Radius\n" + "\n".join(blast_lines))

        # Invariants & Constraints (Tier 4 priority shedding)
        if constraints:
            inv_lines = []
            for inv in constraints:
                gov = inv.get("governing_status", "governing")
                lvl = inv.get("level", "must").upper()
                stmt = inv.get("statement", "")
                title = inv.get("title", "")
                inv_id_raw = inv.get("id") or f"{abs(hash(title)) % 1000000:06d}"
                ref_key = f"ref#inv-{inv_id_raw}"

                if gov == "superseded" and shed_tier >= 1:
                    marker = registry.register(
                        ref_id=ref_key,
                        marker_type="invariant",
                        title=f"Superseded Invariant: {title}",
                        summary=stmt,
                        original_payload=inv,
                    )
                    inv_lines.append(f"- *[SUPERSEDED]* {marker.to_markdown_tag()}")
                elif shed_tier >= 4:
                    marker = registry.register(
                        ref_id=ref_key,
                        marker_type="invariant",
                        title=title,
                        summary=stmt,
                        original_payload=inv,
                    )
                    inv_lines.append(f"- **[{lvl}]** {title}: {marker.to_markdown_tag()}")
                else:
                    inv_lines.append(f"- **[{lvl}]** {title}: {stmt}")

            sections.append(
                "### 📜 Governing Invariants & ADR Constraints\n" + "\n".join(inv_lines)
            )

        # Verified Findings & Claims
        if claims and shed_tier < 5:
            claim_lines = []
            for c in claims[:4] if shed_tier >= 2 else claims:
                st = c.get("statement", "") if isinstance(c, dict) else c.statement
                cl = c.get("classification", "fact") if isinstance(c, dict) else c.classification
                cl_val = cl.value if hasattr(cl, "value") else str(cl)
                claim_lines.append(f"- `[{cl_val.upper()}]` {st}")
            sections.append("### 💡 Verified Claims\n" + "\n".join(claim_lines))

        # Evidence Records (Tier 1 priority shedding - shed first)
        if evidence:
            ev_lines = []
            if shed_tier >= 1:
                # Shed raw snippets into omission registry
                for ev in evidence:
                    ev_id = str(ev.get("id") or ev.get("source_id", "ev"))
                    ref_key = f"ref#ev-{ev_id[:8]}"
                    title = ev.get("title", "Evidence Item")
                    snippet = ev.get("snippet", "")
                    marker = registry.register(
                        ref_id=ref_key,
                        marker_type="evidence",
                        title=title,
                        summary=snippet[:120] + ("..." if len(snippet) > 120 else ""),
                        original_payload=ev if isinstance(ev, dict) else {},
                    )
                    ev_lines.append(f"- {marker.to_markdown_tag()}")
            else:
                for ev in evidence[:6]:
                    ev_lines.append(
                        f"- `[{ev.get('source_type', 'code')}]` **{ev.get('title')}**\n  ```{ev.get('snippet', '')[:100]}```"
                    )

            sections.append("### 🔍 Gathered Evidence & Citations\n" + "\n".join(ev_lines))

        # Unknowns
        if unknowns:
            unknown_lines = [f"- {u}" for u in unknowns[:3]]
            sections.append("### ❓ Known Uncertainties\n" + "\n".join(unknown_lines))

        return "\n\n".join(sections)

    @classmethod
    def _build_dense_agent_json(
        cls,
        brief: Dict[str, Any],
        shed_tier: int,
        registry: OmissionRegistry,
    ) -> Dict[str, Any]:
        """Render compact, token-dense agent JSON projection optimized for LLM/MCP tools."""
        target_files = brief.get("target_files", [])
        target_symbols = brief.get("target_symbols", [])
        signals = brief.get("signals", {})
        claims = brief.get("claims", [])
        constraints = brief.get("constraints", [])
        unknowns = brief.get("unknowns", [])
        recommended_checks = brief.get("recommended_checks", [])
        evidence = brief.get("evidence", [])

        # Core risk block
        risk_sig = signals.get("change_risk", {})
        km = risk_sig.get("kamei_metrics", {})
        risk_block = {
            "score": round(risk_sig.get("risk_score", 0.0), 3),
            "level": risk_sig.get("risk_level", "LOW"),
            "entropy": round(km.get("shannon_entropy", risk_sig.get("shannon_entropy", 0.0)), 3),
            "defect_pressure": round(risk_sig.get("defect_pressure", 0.0), 3),
            "churn": {
                "la": km.get("lines_added", 0),
                "ld": km.get("lines_deleted", 0),
                "nf": km.get("files_touched", len(target_files)),
            },
        }

        # Guarding tests block
        guarding_sig = signals.get("guarding_tests", {})
        ranked_tests = guarding_sig.get("ranked_tests", [])
        untested_files = guarding_sig.get("untested_files", [])

        if shed_tier >= 3:
            tests_block = {
                "untested": untested_files,
                "top_ranked": [
                    {"test": t.get("test_file"), "reach": t.get("reached_target_count")}
                    for t in ranked_tests[:2]
                ],
            }
            if len(ranked_tests) > 2:
                marker = registry.register(
                    ref_id="ref#tests-remaining",
                    marker_type="test",
                    title=f"{len(ranked_tests) - 2} remaining guarding tests",
                    summary="Lower-reach guarding test suites shed for budget",
                    original_payload={"remaining_tests": ranked_tests[2:]},
                )
                tests_block["omitted_tests"] = marker.to_dense_json()
        else:
            tests_block = {
                "untested": untested_files,
                "ranked": [
                    {"test": t.get("test_file"), "reach": t.get("reached_target_count")}
                    for t in ranked_tests
                ],
            }

        # Blast radius block
        blast_sig = signals.get("blast_radius", {})
        affected_comps = blast_sig.get("affected_components", [])
        upstream = blast_sig.get("upstream_callers", [])

        if shed_tier >= 2:
            blast_block = {
                "affected_components": affected_comps,
                "caller_count": len(upstream),
            }
            if upstream:
                marker = registry.register(
                    ref_id="ref#blast-callers",
                    marker_type="blast_node",
                    title="Upstream Callers",
                    summary=f"{len(upstream)} upstream caller paths",
                    original_payload={"upstream": upstream},
                )
                blast_block["omitted_callers"] = marker.to_dense_json()
        else:
            blast_block = {
                "affected_components": affected_comps,
                "callers": [u.get("path") for u in upstream[:6]],
            }

        # Constraints block
        constraints_block = []
        for inv in constraints:
            gov = inv.get("governing_status", "governing")
            inv_id_raw = inv.get("id") or f"{abs(hash(inv.get('title', ''))) % 1000000:06d}"
            ref_key = f"ref#inv-{inv_id_raw}"
            if gov == "superseded" and shed_tier >= 1:
                marker = registry.register(
                    ref_id=ref_key,
                    marker_type="invariant",
                    title=inv.get("title", ""),
                    summary=inv.get("statement", ""),
                    original_payload=inv,
                )
                constraints_block.append(marker.to_dense_json())
            elif shed_tier >= 4:
                marker = registry.register(
                    ref_id=ref_key,
                    marker_type="invariant",
                    title=inv.get("title", ""),
                    summary=inv.get("statement", ""),
                    original_payload=inv,
                )
                constraints_block.append(
                    {
                        "title": inv.get("title"),
                        "level": inv.get("level", "must"),
                        "ref": marker.to_dense_json(),
                    }
                )
            else:
                constraints_block.append(
                    {
                        "title": inv.get("title"),
                        "level": inv.get("level", "must"),
                        "statement": inv.get("statement"),
                        "status": gov,
                    }
                )

        # Evidence block (Tier 1 shedding)
        evidence_block = []
        if evidence:
            if shed_tier >= 1:
                for ev in evidence:
                    ev_id = str(ev.get("id") or ev.get("source_id", "ev"))
                    ref_key = f"ref#ev-{ev_id[:8]}"
                    marker = registry.register(
                        ref_id=ref_key,
                        marker_type="evidence",
                        title=ev.get("title", "Evidence"),
                        summary=ev.get("snippet", "")[:100],
                        original_payload=ev if isinstance(ev, dict) else {},
                    )
                    evidence_block.append(marker.to_dense_json())
            else:
                for ev in evidence[:5]:
                    evidence_block.append(
                        {
                            "type": ev.get("source_type"),
                            "title": ev.get("title"),
                            "path": ev.get("path"),
                        }
                    )

        # Claims block
        claims_data = []
        if claims and shed_tier < 5:
            for c in claims[:3] if shed_tier >= 2 else claims:
                st = c.get("statement", "") if isinstance(c, dict) else c.statement
                cl = c.get("classification", "fact") if isinstance(c, dict) else c.classification
                cl_val = cl.value if hasattr(cl, "value") else str(cl)
                claims_data.append({"type": cl_val, "statement": st})

        # Concurrent overlaps block
        overlap_sig = signals.get("concurrent_overlaps", {})
        overlapping_prs = overlap_sig.get("overlapping_prs", [])
        if overlapping_prs:
            if shed_tier >= 4:
                overlap_block = {
                    "has_direct_conflicts": overlap_sig.get("has_direct_conflicts", False),
                    "highest_risk": overlap_sig.get("highest_risk_level", "NONE"),
                    "top_conflicts": [
                        {
                            "pr": p.get("pr_number"),
                            "author": p.get("pr_author"),
                            "type": p.get("overlap_type"),
                            "files": p.get("overlapping_files", []),
                        }
                        for p in overlapping_prs[:2]
                    ],
                }
            else:
                overlap_block = {
                    "has_direct_conflicts": overlap_sig.get("has_direct_conflicts", False),
                    "has_blast_conflicts": overlap_sig.get("has_blast_conflicts", False),
                    "highest_risk": overlap_sig.get("highest_risk_level", "NONE"),
                    "overlaps": [
                        {
                            "pr": p.get("pr_number"),
                            "title": p.get("pr_title"),
                            "author": p.get("pr_author"),
                            "head_branch": p.get("head_branch"),
                            "risk": p.get("risk_level"),
                            "type": p.get("overlap_type"),
                            "files": p.get("overlapping_files", []),
                            "recommendation": p.get("recommendation"),
                        }
                        for p in overlapping_prs
                    ],
                }
        else:
            overlap_block = {"has_conflicts": False}

        # Code changes block
        code_changes = brief.get("code_changes", [])
        if code_changes:
            if shed_tier >= 4 and len(code_changes) > 3:
                marker = registry.register(
                    ref_id="ref#code-changes-remaining",
                    marker_type="code_change",
                    title=f"{len(code_changes) - 3} Additional Code Modifications",
                    summary="Additional code modifications shed for budget",
                    original_payload={"code_changes": code_changes[3:]},
                )
                code_changes_block = list(code_changes[:3]) + [marker.to_dense_json()]
            else:
                code_changes_block = code_changes
        else:
            code_changes_block = []

        # Assemble dense JSON
        dense = {
            "_schema": "codeatlas.pre_change_brief.v1",
            "_distilled": shed_tier > 0,
            "_shed_tier": shed_tier,
            "intent": brief.get("intent_summary"),
            "targets": {"files": target_files, "symbols": target_symbols},
            "code_changes": code_changes_block,
            "risk": risk_block,
            "guarding_tests": tests_block,
            "blast_radius": blast_block,
            "concurrent_overlaps": overlap_block,
            "constraints": constraints_block,
            "checks": (recommended_checks if shed_tier < 4 else recommended_checks[:3]),
            "claims": claims_data,
            "evidence_refs": evidence_block,
            "unknowns": unknowns if shed_tier < 3 else unknowns[:2],
        }

        return dense

    @classmethod
    def distill_project_context(
        cls,
        ctx_data: Dict[str, Any],
        token_budget: Optional[int] = None,
        output_format: str = "markdown",
        registry: Optional[OmissionRegistry] = None,
    ) -> DistilledResult:
        """Distill canonical ProjectContext into either Human Markdown or Dense Agent JSON."""
        reg = registry or GLOBAL_OMISSION_REGISTRY

        if output_format == "json":
            raw_data = cls._build_project_context_agent_json(ctx_data, shed_tier=0, registry=reg)
            raw_text = json.dumps(raw_data, indent=2)
            est_tokens = estimate_tokens(raw_text)
        else:
            raw_text = cls._build_project_context_markdown(ctx_data, shed_tier=0, registry=reg)
            raw_data = None
            est_tokens = estimate_tokens(raw_text)

        if token_budget is None or est_tokens <= token_budget:
            return DistilledResult(
                content_text=raw_text,
                content_json=raw_data,
                format=output_format,
                token_budget=token_budget,
                estimated_tokens=est_tokens,
                is_distilled=False,
                omitted_count=0,
                omissions=[],
                shed_tier=0,
            )

        omissions_before = len(reg.all_markers())
        chosen_tier = 0
        final_text = raw_text
        final_json = raw_data
        final_tokens = est_tokens

        for tier in range(1, 6):
            if output_format == "json":
                cand_json = cls._build_project_context_agent_json(
                    ctx_data, shed_tier=tier, registry=reg
                )
                cand_text = json.dumps(cand_json, indent=2)
                cand_tokens = estimate_tokens(cand_text)
                final_json = cand_json
                final_text = cand_text
            else:
                cand_text = cls._build_project_context_markdown(
                    ctx_data, shed_tier=tier, registry=reg
                )
                cand_tokens = estimate_tokens(cand_text)
                final_text = cand_text
                final_json = None

            final_tokens = cand_tokens
            chosen_tier = tier

            if cand_tokens <= token_budget:
                break

        current_omissions = reg.all_markers()[omissions_before:]

        return DistilledResult(
            content_text=final_text,
            content_json=final_json,
            format=output_format,
            token_budget=token_budget,
            estimated_tokens=final_tokens,
            is_distilled=True,
            omitted_count=len(current_omissions),
            omissions=current_omissions,
            shed_tier=chosen_tier,
        )

    @classmethod
    def _build_project_context_markdown(
        cls,
        ctx: Dict[str, Any],
        shed_tier: int,
        registry: OmissionRegistry,
    ) -> str:
        """Render canonical ProjectContext Markdown with priority shedding."""
        target_name = ctx.get("target_name", "Target")
        target_type = ctx.get("target_type", "repository")
        confidence = ctx.get("confidence", 1.0)
        provenance = ctx.get("provenance", "tree_sitter_ast")
        summary = ctx.get("summary", "")
        entities = ctx.get("entities", [])
        relationships = ctx.get("relationships", [])
        historical_changes = ctx.get("historical_changes", [])
        related_prs = ctx.get("related_prs", [])
        related_issues = ctx.get("related_issues", [])
        documents = ctx.get("documents", [])
        constraints = ctx.get("design_constraints", [])
        evidence = ctx.get("evidence", [])

        sym_entities = [e for e in entities if e.get("kind") == "symbol"]
        file_entities = [e for e in entities if e.get("kind") == "file"]

        sections = []
        sections.append(f"# Project Context: {target_name}")
        sections.append(
            f"**Target Type:** {target_type.capitalize()} | **Confidence:** {int(confidence * 100)}% | **Provenance:** `{provenance}`"
        )

        if shed_tier > 0:
            sections.append(
                f"> [!NOTE]\n"
                f"> Distilled with Priority Shedding (Tier {shed_tier}). "
                f"Shed elements can be expanded via `[ref#<id>]` tokens."
            )

        sections.append(f"{summary}")

        # Files and symbols
        f_limit = 5 if shed_tier >= 4 else (10 if shed_tier >= 2 else 20)
        s_limit = 5 if shed_tier >= 3 else (15 if shed_tier >= 1 else 30)

        file_items = [
            f"- `{f.get('path')}` ({f.get('language') or 'unknown'})"
            for f in file_entities[:f_limit]
        ]
        if len(file_entities) > f_limit:
            marker = registry.register(
                ref_id=f"ref#ctx-files-{len(file_entities)}",
                marker_type="file",
                title=f"{len(file_entities) - f_limit} additional files",
                summary="Additional indexed files shed for budget",
                original_payload={"files": file_entities[f_limit:]},
            )
            file_items.append(f"- {marker.to_markdown_tag()}")
        sections.append("### 📦 Key Files\n" + ("\n".join(file_items) or "- *None indexed*"))

        sym_items = [
            f"- `{s.get('name')}` ({s.get('path')}:{s.get('line_start')}-{s.get('line_end')})"
            for s in sym_entities[:s_limit]
        ]
        if len(sym_entities) > s_limit:
            marker = registry.register(
                ref_id=f"ref#ctx-syms-{len(sym_entities)}",
                marker_type="symbol",
                title=f"{len(sym_entities) - s_limit} additional symbols",
                summary="Additional indexed symbols shed for budget",
                original_payload={"symbols": sym_entities[s_limit:]},
            )
            sym_items.append(f"- {marker.to_markdown_tag()}")
        sections.append("### 🧩 Indexed Symbols\n" + ("\n".join(sym_items) or "- *None indexed*"))

        # Relationships
        if relationships and shed_tier < 5:
            r_limit = 5 if shed_tier >= 3 else 12
            rel_items = [
                f"- `{r.get('source_name')}` {r.get('type')} `{r.get('target_name')}`"
                for r in relationships[:r_limit]
            ]
            if len(relationships) > r_limit:
                marker = registry.register(
                    ref_id=f"ref#ctx-rels-{len(relationships)}",
                    marker_type="relationship",
                    title=f"{len(relationships) - r_limit} additional relationships",
                    summary="Additional call/import edges shed for budget",
                    original_payload={"relationships": relationships[r_limit:]},
                )
                rel_items.append(f"- {marker.to_markdown_tag()}")
            sections.append("### 🔗 Relationships\n" + "\n".join(rel_items))

        # Historical commits
        if historical_changes and shed_tier < 4:
            c_limit = 3 if shed_tier >= 1 else 8
            hist_items = [
                f"- [`{c.get('commit_hash', '')[:8]}`] {c.get('message', '').splitlines()[0] if c.get('message') else ''} ({c.get('author', '')})"
                for c in historical_changes[:c_limit]
            ]
            if len(historical_changes) > c_limit:
                marker = registry.register(
                    ref_id=f"ref#ctx-commits-{len(historical_changes)}",
                    marker_type="commit",
                    title=f"{len(historical_changes) - c_limit} older commits",
                    summary="Older evolutionary commit records shed for budget",
                    original_payload={"commits": historical_changes[c_limit:]},
                )
                hist_items.append(f"- {marker.to_markdown_tag()}")
            sections.append("### ⏳ Evolution & History\n" + "\n".join(hist_items))

        # Linked PRs and Issues
        if (related_prs or related_issues) and shed_tier < 3:
            pr_lines = [f"- PR #{p.get('pr_number')}: {p.get('title')}" for p in related_prs[:3]]
            issue_lines = [
                f"- Issue #{i.get('issue_number')}: {i.get('title')}" for i in related_issues[:3]
            ]
            sections.append(
                "### 🔀 Provenance Traces\n" + "\n".join((pr_lines + issue_lines) or ["- *None*"])
            )
        elif (related_prs or related_issues) and shed_tier >= 3:
            marker = registry.register(
                ref_id="ref#ctx-prs-issues",
                marker_type="doc",
                title=f"{len(related_prs)} PRs and {len(related_issues)} issues",
                summary="Linked PRs and issues shed for budget",
                original_payload={"prs": related_prs, "issues": related_issues},
            )
            sections.append(f"### 🔀 Provenance Traces\n- {marker.to_markdown_tag()}")

        # Engineering Documents & ADRs
        if documents and shed_tier < 3:
            doc_lines = [f"- **{d.get('title')}** (`{d.get('path')}`)" for d in documents[:3]]
            sections.append("### 📚 Engineering Docs & ADRs\n" + "\n".join(doc_lines))
        elif documents and shed_tier >= 3:
            marker = registry.register(
                ref_id="ref#ctx-docs",
                marker_type="doc",
                title=f"{len(documents)} engineering docs",
                summary="Architecture docs and ADRs shed for budget",
                original_payload={"docs": documents},
            )
            sections.append(f"### 📚 Engineering Docs & ADRs\n- {marker.to_markdown_tag()}")

        # Invariants & Constraints
        if constraints:
            c_lines = []
            for c in constraints:
                lvl = c.get("priority", "MUST").upper()
                dom = c.get("domain", "GENERAL").upper()
                txt = c.get("constraint_text", "")
                if shed_tier >= 4:
                    txt_id = abs(hash(txt)) % 1000000
                    marker = registry.register(
                        ref_id=f"ref#ctx-const-{txt_id:06d}",
                        marker_type="invariant",
                        title=f"Constraint in {dom}",
                        summary=txt,
                        original_payload=c,
                    )
                    c_lines.append(f"- [{dom}] **{lvl}**: {marker.to_markdown_tag()}")
                else:
                    c_lines.append(f"- [{dom}] **{lvl}**: {txt}")
            sections.append("### 📐 Architectural Invariants\n" + "\n".join(c_lines))

        # Evidence records
        if evidence and shed_tier < 4:
            if shed_tier >= 1:
                marker = registry.register(
                    ref_id=f"ref#ctx-ev-all-{len(evidence)}",
                    marker_type="evidence",
                    title=f"{len(evidence)} evidence records",
                    summary="Raw evidence records shed for budget",
                    original_payload={"evidence": evidence},
                )
                sections.append(f"### 📋 Grounded Evidence\n- {marker.to_markdown_tag()}")
            else:
                ev_lines = [
                    f"- `[{e.get('id', '')[:8]}]` {e.get('kind', '')} in `{e.get('source_path', '')}`"
                    for e in evidence[:6]
                ]
                sections.append("### 📋 Grounded Evidence\n" + "\n".join(ev_lines))

        return "\n\n".join(sections)

    @classmethod
    def _build_project_context_agent_json(
        cls,
        ctx: Dict[str, Any],
        shed_tier: int,
        registry: OmissionRegistry,
    ) -> Dict[str, Any]:
        """Render dense Agent JSON for canonical ProjectContext."""
        target_name = ctx.get("target_name", "Target")
        target_type = ctx.get("target_type", "repository")
        confidence = ctx.get("confidence", 1.0)
        summary = ctx.get("summary", "")
        entities = ctx.get("entities", [])
        relationships = ctx.get("relationships", [])
        constraints = ctx.get("design_constraints", [])
        changes = ctx.get("historical_changes", [])

        sym_entities = [e for e in entities if e.get("kind") == "symbol"]
        file_entities = [e for e in entities if e.get("kind") == "file"]

        f_limit = 5 if shed_tier >= 4 else (10 if shed_tier >= 2 else len(file_entities))
        s_limit = 5 if shed_tier >= 3 else (15 if shed_tier >= 1 else len(sym_entities))
        r_limit = 5 if shed_tier >= 3 else (12 if shed_tier >= 1 else len(relationships))

        files_data = [f.get("path") for f in file_entities[:f_limit]]
        symbols_data = [s.get("name") for s in sym_entities[:s_limit]]
        rels_data = [
            {"src": r.get("source_name"), "tgt": r.get("target_name"), "type": r.get("type")}
            for r in relationships[:r_limit]
        ]

        omitted = []
        if len(file_entities) > f_limit:
            marker = registry.register(
                ref_id="ref#ctx-files",
                marker_type="file",
                title=f"{len(file_entities) - f_limit} omitted files",
                summary="Remaining file paths",
                original_payload={"files": [f.get("path") for f in file_entities[f_limit:]]},
            )
            omitted.append(marker.to_dense_json())

        if len(sym_entities) > s_limit:
            marker = registry.register(
                ref_id="ref#ctx-symbols",
                marker_type="symbol",
                title=f"{len(sym_entities) - s_limit} omitted symbols",
                summary="Remaining symbol entities",
                original_payload={"symbols": [s.get("name") for s in sym_entities[s_limit:]]},
            )
            omitted.append(marker.to_dense_json())

        if len(relationships) > r_limit:
            marker = registry.register(
                ref_id="ref#ctx-rels",
                marker_type="relationship",
                title=f"{len(relationships) - r_limit} omitted edges",
                summary="Remaining relationship edges",
                original_payload={"relationships": relationships[r_limit:]},
            )
            omitted.append(marker.to_dense_json())

        return {
            "_schema": "codeatlas.project_context.v1",
            "_distilled": shed_tier > 0,
            "_shed_tier": shed_tier,
            "target": {"name": target_name, "type": target_type, "confidence": confidence},
            "summary": summary,
            "files": files_data,
            "symbols": symbols_data,
            "relationships": rels_data,
            "constraints": [
                {
                    "domain": c.get("domain"),
                    "priority": c.get("priority"),
                    "text": c.get("constraint_text"),
                }
                for c in (constraints[:4] if shed_tier >= 4 else constraints)
            ],
            "change_count": len(changes),
            "omissions": omitted,
        }
