from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.repository import Repository
    from app.models.symbol import Symbol


class SourceFile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "source_files"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding = mapped_column(Vector(1536), nullable=True)

    repository: Mapped["Repository"] = relationship("Repository", back_populates="files")
    symbols: Mapped[List["Symbol"]] = relationship(
        "Symbol", back_populates="file", cascade="all, delete-orphan"
    )
