from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Float, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.commit import Commit
    from app.models.issue import Issue
    from app.models.pull_request import PullRequest


class CommitPullRequestLink(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Associates a commit with a pull request (via reference or merge)."""

    __tablename__ = "commit_pull_request_links"

    commit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("commits.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    pull_request_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("pull_requests.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    pr_number: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    link_type: Mapped[str] = mapped_column(String(50), default="references", nullable=False)
    raw_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    commit: Mapped["Commit"] = relationship("Commit", back_populates="pull_request_links")
    pull_request: Mapped[Optional["PullRequest"]] = relationship(
        "PullRequest", back_populates="commit_links"
    )


class CommitIssueLink(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Associates a commit with an issue (e.g. Fixes #123, Closes #45)."""

    __tablename__ = "commit_issue_links"

    commit_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("commits.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    issue_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("issues.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    issue_number: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    link_type: Mapped[str] = mapped_column(String(50), default="references", nullable=False)
    raw_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    commit: Mapped["Commit"] = relationship("Commit", back_populates="issue_links")
    issue: Mapped[Optional["Issue"]] = relationship("Issue", back_populates="commit_links")


class PullRequestIssueLink(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Associates a pull request with an issue (e.g. PR body 'Fixes #123')."""

    __tablename__ = "pull_request_issue_links"

    pull_request_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("pull_requests.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    issue_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("issues.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    issue_number: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    link_type: Mapped[str] = mapped_column(String(50), default="references", nullable=False)
    raw_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    pull_request: Mapped["PullRequest"] = relationship("PullRequest", back_populates="issue_links")
    issue: Mapped[Optional["Issue"]] = relationship("Issue", back_populates="pull_request_links")
