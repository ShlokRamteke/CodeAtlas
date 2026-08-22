from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.repository import Repository


class PullRequestState(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    MERGED = "merged"


class PullRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "pull_requests"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    number: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(510), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    state: Mapped[PullRequestState] = mapped_column(
        Enum(PullRequestState, name="pull_request_state", native_enum=False),
        default=PullRequestState.OPEN,
        nullable=False,
    )
    author: Mapped[str] = mapped_column(String(255), nullable=False)
    merged_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    embedding = mapped_column(Vector(1536), nullable=True)

    repository: Mapped["Repository"] = relationship("Repository", back_populates="pull_requests")
