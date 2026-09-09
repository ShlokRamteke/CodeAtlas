from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from sqlalchemy import JSON, Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.design_constraint import DesignConstraint
    from app.models.repository import Repository


class EngineeringDocType(str, enum.Enum):
    README = "readme"
    ARCHITECTURE = "architecture"
    ADR = "adr"
    DESIGN_DOC = "design_doc"
    TESTING_GUIDE = "testing_guide"
    GENERAL_DOC = "general_doc"


class ADRStatus(str, enum.Enum):
    ACCEPTED = "accepted"
    SUPERSEDED = "superseded"
    PROPOSED = "proposed"
    DEPRECATED = "deprecated"
    DRAFT = "draft"
    NA = "n/a"


class EngineeringDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "engineering_docs"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    path: Mapped[str] = mapped_column(String(1024), index=True, nullable=False)
    doc_type: Mapped[EngineeringDocType] = mapped_column(
        Enum(EngineeringDocType, name="engineering_doc_type", native_enum=False),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(510), nullable=False)
    format: Mapped[str] = mapped_column(String(50), default="markdown", nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[ADRStatus] = mapped_column(
        Enum(ADRStatus, name="adr_status", native_enum=False),
        default=ADRStatus.NA,
        nullable=False,
    )
    deciders: Mapped[Optional[str]] = mapped_column(String(510), nullable=True)
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=dict, nullable=False
    )

    repository: Mapped["Repository"] = relationship("Repository", back_populates="engineering_docs")
    constraints: Mapped[List["DesignConstraint"]] = relationship(
        "DesignConstraint", back_populates="document", cascade="all, delete-orphan"
    )
