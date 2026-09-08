from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import JSON, Enum, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.engineering_doc import EngineeringDocument
    from app.models.repository import Repository


class ConstraintCategory(str, enum.Enum):
    SECURITY = "security"
    PERFORMANCE = "performance"
    ARCHITECTURE = "architecture"
    TESTING = "testing"
    DATA_INTEGRITY = "data_integrity"
    GENERAL = "general"


class ConstraintLevel(str, enum.Enum):
    MUST = "must"
    SHOULD = "should"
    MUST_NOT = "must_not"


class DesignConstraint(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "design_constraints"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("engineering_docs.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    category: Mapped[ConstraintCategory] = mapped_column(
        Enum(ConstraintCategory, name="constraint_category", native_enum=False),
        index=True,
        nullable=False,
    )
    level: Mapped[ConstraintLevel] = mapped_column(
        Enum(ConstraintLevel, name="constraint_level", native_enum=False),
        default=ConstraintLevel.MUST,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(510), nullable=False)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    source_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    line_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    line_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    extra_metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=dict, nullable=False
    )

    repository: Mapped["Repository"] = relationship("Repository")
    document: Mapped[Optional["EngineeringDocument"]] = relationship(
        "EngineeringDocument", back_populates="constraints"
    )
