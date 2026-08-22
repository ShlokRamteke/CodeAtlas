from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.repository import Repository
    from app.models.source_file import SourceFile


class DependencyKind(str, enum.Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"
    RELATIVE = "relative"


class CodeDependency(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "code_dependencies"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    source_file_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("source_files.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    source_path: Mapped[str] = mapped_column(String(1024), index=True, nullable=False)
    target_path: Mapped[str] = mapped_column(String(1024), index=True, nullable=False)
    imported_symbol: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    kind: Mapped[DependencyKind] = mapped_column(
        Enum(DependencyKind, name="dependency_kind", native_enum=False),
        default=DependencyKind.INTERNAL,
        nullable=False,
    )

    repository: Mapped["Repository"] = relationship("Repository", back_populates="dependencies")
    source_file: Mapped["SourceFile"] = relationship("SourceFile", back_populates="dependencies")
