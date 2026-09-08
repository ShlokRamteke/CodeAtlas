from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.commit import Commit
    from app.models.dependency import CodeDependency
    from app.models.engineering_doc import EngineeringDocument
    from app.models.investigation import Investigation
    from app.models.issue import Issue
    from app.models.pull_request import PullRequest
    from app.models.source_file import SourceFile


class RepositoryStatus(str, enum.Enum):
    IDLE = "idle"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


class Repository(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "repositories"

    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(510), unique=True, index=True, nullable=False)
    default_branch: Mapped[str] = mapped_column(String(255), default="main", nullable=False)
    status: Mapped[RepositoryStatus] = mapped_column(
        Enum(RepositoryStatus, name="repository_status", native_enum=False),
        default=RepositoryStatus.IDLE,
        nullable=False,
    )
    indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    file_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    symbol_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    commit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    files: Mapped[List["SourceFile"]] = relationship(
        "SourceFile", back_populates="repository", cascade="all, delete-orphan"
    )
    dependencies: Mapped[List["CodeDependency"]] = relationship(
        "CodeDependency", back_populates="repository", cascade="all, delete-orphan"
    )
    commits: Mapped[List["Commit"]] = relationship(
        "Commit", back_populates="repository", cascade="all, delete-orphan"
    )
    pull_requests: Mapped[List["PullRequest"]] = relationship(
        "PullRequest", back_populates="repository", cascade="all, delete-orphan"
    )
    issues: Mapped[List["Issue"]] = relationship(
        "Issue", back_populates="repository", cascade="all, delete-orphan"
    )
    investigations: Mapped[List["Investigation"]] = relationship(
        "Investigation", back_populates="repository", cascade="all, delete-orphan"
    )
    engineering_docs: Mapped[List["EngineeringDocument"]] = relationship(
        "EngineeringDocument", back_populates="repository", cascade="all, delete-orphan"
    )
