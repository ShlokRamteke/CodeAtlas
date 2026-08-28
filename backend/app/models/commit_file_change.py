from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Enum, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.commit import Commit


class ChangeType(str, enum.Enum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class CommitFileChange(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "commit_file_changes"

    commit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("commits.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(String(1024), index=True, nullable=False)
    change_type: Mapped[ChangeType] = mapped_column(
        Enum(
            ChangeType,
            name="change_type_enum",
            native_enum=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=ChangeType.MODIFIED,
    )

    insertions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deletions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    old_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    commit: Mapped["Commit"] = relationship("Commit", back_populates="file_changes")
