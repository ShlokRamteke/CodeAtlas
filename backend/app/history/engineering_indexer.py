from __future__ import annotations

import hashlib
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.engine import redact_secrets
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
from app.parser.doc_parser import (
    EngineeringContextParser,
    ParsedEngineeringDoc,
)


class EngineeringContextIndexer:
    """
    Service for indexing repository documentation, Architecture Decision Records (ADRs),
    and architectural invariants / design constraints.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.parser = EngineeringContextParser()

    @staticmethod
    def compute_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    async def index_document(
        self,
        repository_id: uuid.UUID,
        path: str,
        raw_content: str,
    ) -> EngineeringDocument:
        """Sanitize, parse, and persist an engineering document and its extracted constraints."""
        sanitized = redact_secrets(raw_content)
        content_hash = self.compute_hash(sanitized)

        parsed: ParsedEngineeringDoc = self.parser.parse_doc(path, sanitized, content_hash)

        # Check existing document for upsert
        stmt = select(EngineeringDocument).where(
            EngineeringDocument.repository_id == repository_id,
            EngineeringDocument.path == path,
        )
        result = await self.session.execute(stmt)
        doc = result.scalar_one_or_none()

        doc_type_val = EngineeringDocType(parsed.doc_type.value)
        status_val = ADRStatus(parsed.status.value)

        if doc:
            doc.doc_type = doc_type_val
            doc.title = parsed.title
            doc.format = parsed.format
            doc.content_hash = content_hash
            doc.status = status_val
            doc.deciders = parsed.deciders
            doc.raw_content = sanitized
            doc.summary = parsed.summary
            doc.extra_metadata = parsed.extra_metadata
            # Remove old constraints
            await self.session.execute(
                delete(DesignConstraint).where(DesignConstraint.document_id == doc.id)
            )
        else:
            doc = EngineeringDocument(
                id=uuid.uuid4(),
                repository_id=repository_id,
                path=path,
                doc_type=doc_type_val,
                title=parsed.title,
                format=parsed.format,
                content_hash=content_hash,
                status=status_val,
                deciders=parsed.deciders,
                raw_content=sanitized,
                summary=parsed.summary,
                extra_metadata=parsed.extra_metadata,
            )
            self.session.add(doc)

        await self.session.flush()

        # Insert extracted design constraints
        for c in parsed.constraints:
            cat_val = ConstraintCategory(c.category.value)
            lvl_val = ConstraintLevel(c.level.value)
            constraint = DesignConstraint(
                id=uuid.uuid4(),
                repository_id=repository_id,
                document_id=doc.id,
                category=cat_val,
                level=lvl_val,
                title=c.title,
                statement=c.statement,
                source_path=path,
                line_start=c.line_start,
                line_end=c.line_end,
                confidence=c.confidence,
                extra_metadata=c.extra_metadata,
            )
            self.session.add(constraint)

        await self.session.commit()
        await self.session.refresh(doc)
        return doc

    async def index_repository_docs(
        self,
        repository_id: uuid.UUID,
        files: Dict[str, str],
    ) -> List[EngineeringDocument]:
        """Bulk index documentation files in a repository."""
        doc_extensions = {".md", ".markdown", ".rst", ".txt", ".adoc"}
        indexed_docs: List[EngineeringDocument] = []

        for path, content in files.items():
            ext = "." + path.split(".")[-1].lower() if "." in path else ""
            fname = path.split("/")[-1].lower()
            if ext in doc_extensions or fname in (
                "readme",
                "contributing",
                "architecture",
                "decisions",
            ):
                doc = await self.index_document(repository_id, path, content)
                indexed_docs.append(doc)

        return indexed_docs

    async def get_docs(
        self,
        repository_id: uuid.UUID,
        doc_type: Optional[EngineeringDocType] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[EngineeringDocument]:
        """Fetch engineering documents for a repository with optional doc_type filtering."""
        stmt = select(EngineeringDocument).where(EngineeringDocument.repository_id == repository_id)
        if doc_type:
            stmt = stmt.where(EngineeringDocument.doc_type == doc_type)

        stmt = (
            stmt.order_by(EngineeringDocument.doc_type, EngineeringDocument.path)
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_doc_by_id(
        self,
        repository_id: uuid.UUID,
        doc_id: uuid.UUID,
    ) -> Optional[EngineeringDocument]:
        """Fetch a single engineering document by ID with associated constraints."""
        stmt = select(EngineeringDocument).where(
            EngineeringDocument.repository_id == repository_id,
            EngineeringDocument.id == doc_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_adrs(
        self,
        repository_id: uuid.UUID,
        status: Optional[ADRStatus] = None,
    ) -> List[EngineeringDocument]:
        """Fetch all Architecture Decision Records (ADRs) with optional status filter."""
        stmt = select(EngineeringDocument).where(
            EngineeringDocument.repository_id == repository_id,
            EngineeringDocument.doc_type == EngineeringDocType.ADR,
        )
        if status:
            stmt = stmt.where(EngineeringDocument.status == status)

        stmt = stmt.order_by(EngineeringDocument.path)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_constraints(
        self,
        repository_id: uuid.UUID,
        category: Optional[ConstraintCategory] = None,
        level: Optional[ConstraintLevel] = None,
        source_path: Optional[str] = None,
        limit: int = 100,
    ) -> List[DesignConstraint]:
        """Fetch extracted design constraints and architectural invariants."""
        stmt = select(DesignConstraint).where(DesignConstraint.repository_id == repository_id)
        if category:
            stmt = stmt.where(DesignConstraint.category == category)
        if level:
            stmt = stmt.where(DesignConstraint.level == level)
        if source_path:
            stmt = stmt.where(DesignConstraint.source_path.ilike(f"%{source_path}%"))

        stmt = stmt.order_by(DesignConstraint.category, DesignConstraint.source_path).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search_engineering_context(
        self,
        repository_id: uuid.UUID,
        query: str,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        Deterministic search across engineering documents and constraints.
        Returns matched docs, matched constraints, and ranked relevance scores.
        """
        terms = [t.strip().lower() for t in query.split() if t.strip()]
        if not terms:
            return {"docs": [], "constraints": [], "total_matches": 0}

        # Search documents
        doc_stmt = select(EngineeringDocument).where(
            EngineeringDocument.repository_id == repository_id
        )
        doc_res = await self.session.execute(doc_stmt)
        all_docs = list(doc_res.scalars().all())

        matched_docs = []
        for doc in all_docs:
            searchable = (
                f"{doc.title} {doc.path} {doc.summary or ''} {doc.raw_content[:2000]}".lower()
            )
            score = 0.0
            for term in terms:
                if term in doc.title.lower():
                    score += 3.0
                if term in doc.path.lower():
                    score += 2.0
                if term in searchable:
                    score += 1.0
            if score > 0:
                matched_docs.append(
                    {
                        "id": str(doc.id),
                        "path": doc.path,
                        "title": doc.title,
                        "doc_type": doc.doc_type.value,
                        "status": doc.status.value,
                        "summary": doc.summary,
                        "relevance_score": score,
                    }
                )

        matched_docs.sort(key=lambda d: d["relevance_score"], reverse=True)

        # Search constraints
        constraint_stmt = select(DesignConstraint).where(
            DesignConstraint.repository_id == repository_id
        )
        c_res = await self.session.execute(constraint_stmt)
        all_constraints = list(c_res.scalars().all())

        matched_constraints = []
        for c in all_constraints:
            searchable = f"{c.title} {c.statement} {c.category.value} {c.source_path}".lower()
            score = 0.0
            for term in terms:
                if term in c.title.lower():
                    score += 3.0
                if term in c.statement.lower():
                    score += 2.0
                if term in searchable:
                    score += 1.0
            if score > 0:
                matched_constraints.append(
                    {
                        "id": str(c.id),
                        "title": c.title,
                        "statement": c.statement,
                        "category": c.category.value,
                        "level": c.level.value,
                        "source_path": c.source_path,
                        "line_start": c.line_start,
                        "line_end": c.line_end,
                        "confidence": c.confidence,
                        "relevance_score": score,
                    }
                )

        matched_constraints.sort(key=lambda c: c["relevance_score"], reverse=True)

        return {
            "query": query,
            "docs": matched_docs[:limit],
            "constraints": matched_constraints[:limit],
            "total_matches": len(matched_docs) + len(matched_constraints),
        }
