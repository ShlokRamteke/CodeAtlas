from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Enum, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.source_file import SourceFile


class SymbolKind(str, enum.Enum):
    FUNCTION = "function"
    CLASS = "class"
    INTERFACE = "interface"
    TYPE = "type"
    VARIABLE = "variable"
    CONSTANT = "constant"
    MODULE = "module"
    METHOD = "method"


class Symbol(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "symbols"

    file_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_files.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    kind: Mapped[SymbolKind] = mapped_column(
        Enum(SymbolKind, name="symbol_kind", native_enum=False),
        nullable=False,
    )
    line_start: Mapped[int] = mapped_column(Integer, nullable=False)
    line_end: Mapped[int] = mapped_column(Integer, nullable=False)
    signature: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    docstring: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding = mapped_column(Vector(1536), nullable=True)

    file: Mapped["SourceFile"] = relationship("SourceFile", back_populates="symbols")
