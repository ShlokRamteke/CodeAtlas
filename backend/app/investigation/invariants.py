from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.commit import Commit
from app.models.commit_file_change import ChangeType, CommitFileChange
from app.models.design_constraint import (
    ConstraintCategory,
    ConstraintLevel,
    DesignConstraint,
)
from app.models.engineering_doc import (
    ADRStatus,
    EngineeringDocType,
    EngineeringDocument,
)
from app.models.historical_link import CommitPullRequestLink
from app.parser.doc_parser import (
    EngineeringContextParser,
    ParsedEngineeringDoc,
)


@dataclass
class SynthesizedInvariant:
    id: str
    title: str
    statement: str
    level: str  # "must" | "should" | "must_not"
    category: str  # "security" | "architecture" | "performance" | "testing" | "data_integrity" | "general"
    governing_status: str  # "governing" | "superseded" | "proposed" | "deprecated"
    superseded_by: Optional[str] = None
    source_doc_title: str = ""
    source_doc_path: str = ""
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    rationale: str = ""
    origin_commit_hash: Optional[str] = None
    origin_commit_message: Optional[str] = None
    origin_pr_number: Optional[int] = None
    origin_pr_title: Optional[str] = None
    origin_author: Optional[str] = None
    relevant_files: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "statement": self.statement,
            "level": self.level,
            "category": self.category,
            "governing_status": self.governing_status,
            "superseded_by": self.superseded_by,
            "source_doc_title": self.source_doc_title,
            "source_doc_path": self.source_doc_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "rationale": self.rationale,
            "origin_commit_hash": self.origin_commit_hash,
            "origin_commit_message": self.origin_commit_message,
            "origin_pr_number": self.origin_pr_number,
            "origin_pr_title": self.origin_pr_title,
            "origin_author": self.origin_author,
            "relevant_files": self.relevant_files,
        }


class InvariantSynthesizer:
    """
    Synthesizes architectural invariants, ADR decisions, RFC 2119 design rules,
    and historical origin intent (origin commits & PR rationale).
    """

    SUPERSEDED_BY_REGEX = re.compile(
        r"(?i)(?:superseded\s+by|replaced\s+by)\s*[:\-\[]*\s*([A-Za-z0-9_\-./]+)",
    )
    SUPERSEDES_REGEX = re.compile(
        r"(?i)(?:supersedes|replaces)\s*[:\-\[]*\s*([A-Za-z0-9_\-./]+)",
    )

    @classmethod
    def resolve_governing_status(
        cls,
        doc_status: ADRStatus,
        doc_path: str,
        doc_title: str,
        raw_content: str,
        all_docs: List[Any],
    ) -> Tuple[str, Optional[str]]:
        """
        Determines if a document is 'governing', 'superseded', 'proposed', or 'deprecated'.
        Also identifies superseding document references.
        """
        superseded_by: Optional[str] = None

        # 1. Check explicit document status
        if doc_status in (ADRStatus.SUPERSEDED,):
            m = cls.SUPERSEDED_BY_REGEX.search(raw_content)
            if m:
                superseded_by = m.group(1).strip("[]()., ")
            return "superseded", superseded_by

        if doc_status in (ADRStatus.DEPRECATED,):
            return "deprecated", None

        if doc_status in (ADRStatus.PROPOSED, ADRStatus.DRAFT):
            return "proposed", None

        # 2. Check if text explicitly says "Superseded by"
        sup_match = cls.SUPERSEDED_BY_REGEX.search(raw_content)
        if sup_match:
            superseded_by = sup_match.group(1).strip("[]()., ")
            return "superseded", superseded_by

        # 3. Cross-reference other documents: does another accepted document say it supersedes this one?
        doc_identifiers = {
            doc_path.lower(),
            doc_path.split("/")[-1].lower(),
            doc_title.lower(),
        }
        for token in re.findall(r"(?:adr[-_]?)?\d{1,4}", doc_path.lower() + " " + doc_title.lower()):
            clean_tok = token.replace("_", "-")
            doc_identifiers.add(clean_tok)
            num_part = re.sub(r"\D", "", clean_tok)
            if num_part:
                doc_identifiers.add(num_part)
                doc_identifiers.add(f"adr-{num_part}")
                try:
                    num_int = int(num_part)
                    doc_identifiers.add(f"adr-{num_int}")
                    doc_identifiers.add(f"adr-{num_int:04d}")
                    doc_identifiers.add(f"adr-{num_int:03d}")
                except ValueError:
                    pass

        for other in all_docs:
            other_content = getattr(other, "raw_content", "") or (other.get("raw_content", "") if isinstance(other, dict) else "")
            other_title = getattr(other, "title", "") or (other.get("title", "") if isinstance(other, dict) else "")
            other_path = getattr(other, "path", "") or (other.get("path", "") if isinstance(other, dict) else "")

            if other_path == doc_path or other_title == doc_title:
                continue

            for m in cls.SUPERSEDES_REGEX.finditer(other_content):
                target_ref = m.group(1).lower().strip("[]()., ")
                target_num = re.sub(r"\D", "", target_ref)
                if (
                    target_ref in doc_identifiers
                    or (target_num and target_num in doc_identifiers)
                    or any(ident in target_ref for ident in doc_identifiers if len(ident) > 3)
                ):
                    return "superseded", other_title or str(other_path)

        return "governing", None

    @classmethod
    async def extract_origin_intent_for_targets(
        cls,
        db: Optional[AsyncSession],
        repository_id: uuid.UUID,
        target_files: List[str],
        file_commits: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Extracts origin / introducing commits, author, and linked PR rationale
        for the given target files.
        """
        origin_intent_map: Dict[str, Dict[str, Any]] = {}

        if not target_files:
            return origin_intent_map

        clean_paths = [f.lstrip("/") for f in target_files]

        if db is not None:
            try:
                stmt = (
                    select(CommitFileChange, Commit)
                    .join(Commit, CommitFileChange.commit_id == Commit.id)
                    .options(
                        selectinload(Commit.pull_request_links).selectinload(
                            CommitPullRequestLink.pull_request
                        )
                    )
                    .where(
                        Commit.repository_id == repository_id,
                        CommitFileChange.file_path.in_(clean_paths),
                    )
                    .order_by(Commit.committed_at.asc())
                )
                res = await db.execute(stmt)
                rows = res.all()

                for cfc, commit in rows:
                    p = cfc.file_path
                    if p not in origin_intent_map or cfc.change_type == ChangeType.ADDED:
                        pr_num: Optional[int] = None
                        pr_title: Optional[str] = None
                        pr_body: Optional[str] = None
                        if commit.pull_request_links:
                            pr_link = commit.pull_request_links[0]
                            pr_num = pr_link.pr_number
                            if pr_link.pull_request:
                                pr_title = pr_link.pull_request.title
                                pr_body = pr_link.pull_request.body

                        origin_intent_map[p] = {
                            "commit_hash": commit.commit_hash,
                            "commit_message": commit.message,
                            "author": commit.author_name,
                            "committed_at": commit.committed_at,
                            "pr_number": pr_num,
                            "pr_title": pr_title,
                            "pr_body": pr_body,
                        }
            except Exception:
                pass

        if file_commits:
            for tf in clean_paths:
                if tf not in origin_intent_map and file_commits:
                    earliest = file_commits[-1]
                    msg = earliest.get("message", "")
                    pr_num = None
                    pr_match = re.search(r"(?:#|GH-)(\d+)", msg)
                    if pr_match:
                        pr_num = int(pr_match.group(1))

                    origin_intent_map[tf] = {
                        "commit_hash": earliest.get("hash", "unknown"),
                        "commit_message": msg,
                        "author": earliest.get("author", "Developer"),
                        "committed_at": earliest.get("committed_at"),
                        "pr_number": pr_num,
                        "pr_title": msg.split("\n")[0] if msg else None,
                        "pr_body": msg,
                    }

        return origin_intent_map

    @classmethod
    async def synthesize_invariants(
        cls,
        repository_id: uuid.UUID,
        target_files: List[str],
        target_symbols: Optional[List[str]] = None,
        db: Optional[AsyncSession] = None,
        engineering_docs: Optional[List[Dict[str, Any]]] = None,
        file_commits: Optional[List[Dict[str, Any]]] = None,
    ) -> List[SynthesizedInvariant]:
        """
        Synthesizes architectural invariants, ADR governing decisions,
        RFC 2119 constraints, and origin intent rationale.
        """
        target_symbols = target_symbols or []
        clean_target_files = [f.lstrip("/") for f in target_files]
        invariants: List[SynthesizedInvariant] = []

        origin_intent = await cls.extract_origin_intent_for_targets(
            db=db,
            repository_id=repository_id,
            target_files=target_files,
            file_commits=file_commits,
        )

        all_docs: List[Any] = []
        raw_constraints: List[Any] = []

        if db is not None:
            try:
                doc_stmt = select(EngineeringDocument).where(
                    EngineeringDocument.repository_id == repository_id
                )
                doc_res = await db.execute(doc_stmt)
                all_docs = list(doc_res.scalars().all())

                c_stmt = (
                    select(DesignConstraint)
                    .options(selectinload(DesignConstraint.document))
                    .where(DesignConstraint.repository_id == repository_id)
                )
                c_res = await db.execute(c_stmt)
                raw_constraints = list(c_res.scalars().all())
            except Exception:
                all_docs = []
                raw_constraints = []

        if engineering_docs:
            parser = EngineeringContextParser()
            for doc_dict in engineering_docs:
                path = doc_dict.get("path") or doc_dict.get("id") or "docs/adr/0001-architecture.md"
                content = doc_dict.get("raw_content") or doc_dict.get("summary") or ""
                parsed_doc = parser.parse_doc(path, content, "")
                all_docs.append(parsed_doc)
                for c in parsed_doc.constraints:
                    c.extra_metadata["doc_title"] = parsed_doc.title
                    c.extra_metadata["doc_path"] = path
                    c.extra_metadata["doc_status"] = parsed_doc.status.value
                    c.extra_metadata["raw_content"] = content
                    raw_constraints.append(c)

        seen_statements: Set[str] = set()

        for c in raw_constraints:
            statement = getattr(c, "statement", "") or ""
            title = getattr(c, "title", "") or ""
            stmt_clean = statement.strip().lower()
            if not stmt_clean or stmt_clean in seen_statements:
                continue

            level_obj = getattr(c, "level", None)
            level_str = level_obj.value if hasattr(level_obj, "value") else str(level_obj or "must").lower()

            cat_obj = getattr(c, "category", None)
            cat_str = cat_obj.value if hasattr(cat_obj, "value") else str(cat_obj or "architecture").lower()

            doc = getattr(c, "document", None)
            if doc is not None:
                doc_path = doc.path
                doc_title = doc.title
                doc_status = doc.status
                raw_content = doc.raw_content
            else:
                extra = getattr(c, "extra_metadata", {}) or {}
                doc_path = extra.get("doc_path", getattr(c, "source_path", ""))
                doc_title = extra.get("doc_title", "Architectural Invariant")
                raw_status = extra.get("doc_status", "accepted")
                try:
                    doc_status = ADRStatus(raw_status)
                except Exception:
                    doc_status = ADRStatus.ACCEPTED
                raw_content = extra.get("raw_content", "")

            is_relevant = False
            relevant_target_files: List[str] = []

            for tf in clean_target_files:
                tf_base = tf.split("/")[-1]
                if tf.lower() in doc_path.lower() or tf.lower() in statement.lower() or tf_base.lower() in statement.lower():
                    is_relevant = True
                    relevant_target_files.append(tf)

            for sym in target_symbols:
                if sym.lower() in statement.lower() or sym.lower() in title.lower():
                    is_relevant = True

            if (
                cat_str in ("security", "architecture", "data_integrity", "performance")
                or "adr" in doc_path.lower()
                or "decision" in doc_path.lower()
            ):
                is_relevant = True
                if not relevant_target_files and clean_target_files:
                    relevant_target_files = clean_target_files[:2]

            if not is_relevant:
                continue

            gov_status, superseded_by = cls.resolve_governing_status(
                doc_status=doc_status,
                doc_path=doc_path,
                doc_title=doc_title,
                raw_content=raw_content,
                all_docs=all_docs,
            )

            origin_info = None
            for rf in relevant_target_files:
                if rf in origin_intent:
                    origin_info = origin_intent[rf]
                    break
            if not origin_info and origin_intent:
                origin_info = next(iter(origin_intent.values()))

            rationale_parts = []
            if gov_status == "governing":
                rationale_parts.append(f"Governing {cat_str.upper()} constraint defined in '{doc_title}'.")
            elif gov_status == "superseded":
                ref_text = f" by {superseded_by}" if superseded_by else ""
                rationale_parts.append(f"SUPERSEDED decision{ref_text} (formerly defined in '{doc_title}').")
            else:
                rationale_parts.append(f"{gov_status.capitalize()} constraint from '{doc_title}'.")

            if origin_info:
                commit_msg = (origin_info.get("commit_message") or "").split("\n")[0][:60]
                hash_short = (origin_info.get("commit_hash") or "")[:7]
                pr_num = origin_info.get("pr_number")
                pr_title = origin_info.get("pr_title")

                prov = f"Introduced in commit {hash_short}"
                if pr_num:
                    prov += f" (PR #{pr_num}{f': {pr_title[:40]}' if pr_title else ''})"
                prov += f" by {origin_info.get('author', 'Developer')}"
                if commit_msg:
                    prov += f" — '{commit_msg}'"
                rationale_parts.append(prov)

            rationale_parts.append(f"Requires: {statement}")

            inv_obj = SynthesizedInvariant(
                id=f"inv-{len(invariants) + 1}",
                title=title or f"{cat_str.capitalize()} Invariant: {statement[:40]}...",
                statement=statement,
                level=level_str,
                category=cat_str,
                governing_status=gov_status,
                superseded_by=superseded_by,
                source_doc_title=doc_title,
                source_doc_path=doc_path,
                line_start=getattr(c, "line_start", None),
                line_end=getattr(c, "line_end", None),
                rationale=" ".join(rationale_parts),
                origin_commit_hash=origin_info.get("commit_hash") if origin_info else None,
                origin_commit_message=origin_info.get("commit_message") if origin_info else None,
                origin_pr_number=origin_info.get("pr_number") if origin_info else None,
                origin_pr_title=origin_info.get("pr_title") if origin_info else None,
                origin_author=origin_info.get("author") if origin_info else None,
                relevant_files=relevant_target_files,
            )
            invariants.append(inv_obj)
            seen_statements.add(stmt_clean)

        return invariants
