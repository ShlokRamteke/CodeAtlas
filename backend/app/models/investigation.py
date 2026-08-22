from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import Enum, ForeignKey, Integer, JSON, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.repository import Repository
    from app.models.evidence import Evidence


class InvestigationType(str, enum.Enum):
    UNDERSTAND = "understand"
    WHY = "why"
    HISTORY = "history"
    BEFORE_CHANGE = "before_change"


class InvestigationStatus(str, enum.Enum):
    PENDING = "pending"
    PLANNING = "planning"
    GATHERING = "gathering"
    REASONING = "reasoning"
    COMPLETED = "completed"
    FAILED = "failed"


class Investigation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "investigations"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[InvestigationType] = mapped_column(
        Enum(InvestigationType, name="investigation_type", native_enum=False),
        default=InvestigationType.UNDERSTAND,
        nullable=False,
    )
    status: Mapped[InvestigationStatus] = mapped_column(
        Enum(InvestigationStatus, name="investigation_status", native_enum=False),
        default=InvestigationStatus.PENDING,
        nullable=False,
    )
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    claims: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), default=list, nullable=False
    )
    token_usage: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    repository: Mapped["Repository"] = relationship("Repository", back_populates="investigations")
    evidence: Mapped[List["Evidence"]] = relationship(
        "Evidence", back_populates="investigation", cascade="all, delete-orphan"
    )
