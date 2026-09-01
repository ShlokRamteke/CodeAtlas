from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.commit_file_change import CommitFileChange
    from app.models.historical_link import CommitIssueLink, CommitPullRequestLink
    from app.models.repository import Repository


class Commit(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "commits"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    commit_hash: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    author_name: Mapped[str] = mapped_column(String(255), nullable=False)
    author_email: Mapped[str] = mapped_column(String(255), nullable=False)
    committed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    parent_hashes: Mapped[Optional[List[str]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True, default=list
    )

    files_changed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    insertions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deletions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    embedding = mapped_column(Vector(1536), nullable=True)

    repository: Mapped["Repository"] = relationship("Repository", back_populates="commits")
    file_changes: Mapped[List["CommitFileChange"]] = relationship(
        "CommitFileChange",
        back_populates="commit",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    pull_request_links: Mapped[List["CommitPullRequestLink"]] = relationship(
        "CommitPullRequestLink",
        back_populates="commit",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    issue_links: Mapped[List["CommitIssueLink"]] = relationship(
        "CommitIssueLink",
        back_populates="commit",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
