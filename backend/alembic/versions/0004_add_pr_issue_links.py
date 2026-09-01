"""add pr and issue metadata columns and historical link tables
Revision ID: 0004_add_pr_issue_links
Revises: 0003_add_commit_file_changes
Create Date: 2026-08-28 12:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0004_add_pr_issue_links"
down_revision: str | None = "0003_add_commit_file_changes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Enhance pull_requests table
    op.add_column(
        "pull_requests", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("pull_requests", sa.Column("labels", JSONB, nullable=True))
    op.add_column("pull_requests", sa.Column("html_url", sa.String(510), nullable=True))

    # 2. Enhance issues table
    op.add_column("issues", sa.Column("labels", JSONB, nullable=True))
    op.add_column("issues", sa.Column("html_url", sa.String(510), nullable=True))

    # 3. Create commit_pull_request_links table
    op.create_table(
        "commit_pull_request_links",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "commit_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("commits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "pull_request_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("pull_requests.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("pr_number", sa.Integer(), nullable=False),
        sa.Column("link_type", sa.String(50), nullable=False, server_default="references"),
        sa.Column("raw_reference", sa.String(255), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_commit_pull_request_links_commit_id", "commit_pull_request_links", ["commit_id"]
    )
    op.create_index(
        "ix_commit_pull_request_links_pull_request_id",
        "commit_pull_request_links",
        ["pull_request_id"],
    )
    op.create_index(
        "ix_commit_pull_request_links_pr_number", "commit_pull_request_links", ["pr_number"]
    )

    # 4. Create commit_issue_links table
    op.create_table(
        "commit_issue_links",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "commit_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("commits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "issue_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("issues.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("issue_number", sa.Integer(), nullable=False),
        sa.Column("link_type", sa.String(50), nullable=False, server_default="references"),
        sa.Column("raw_reference", sa.String(255), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_commit_issue_links_commit_id", "commit_issue_links", ["commit_id"])
    op.create_index("ix_commit_issue_links_issue_id", "commit_issue_links", ["issue_id"])
    op.create_index("ix_commit_issue_links_issue_number", "commit_issue_links", ["issue_number"])

    # 5. Create pull_request_issue_links table
    op.create_table(
        "pull_request_issue_links",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "pull_request_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("pull_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "issue_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("issues.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("issue_number", sa.Integer(), nullable=False),
        sa.Column("link_type", sa.String(50), nullable=False, server_default="references"),
        sa.Column("raw_reference", sa.String(255), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_pull_request_issue_links_pull_request_id",
        "pull_request_issue_links",
        ["pull_request_id"],
    )
    op.create_index(
        "ix_pull_request_issue_links_issue_id", "pull_request_issue_links", ["issue_id"]
    )
    op.create_index(
        "ix_pull_request_issue_links_issue_number", "pull_request_issue_links", ["issue_number"]
    )


def downgrade() -> None:
    op.drop_index("ix_pull_request_issue_links_issue_number", table_name="pull_request_issue_links")
    op.drop_index("ix_pull_request_issue_links_issue_id", table_name="pull_request_issue_links")
    op.drop_index(
        "ix_pull_request_issue_links_pull_request_id", table_name="pull_request_issue_links"
    )
    op.drop_table("pull_request_issue_links")

    op.drop_index("ix_commit_issue_links_issue_number", table_name="commit_issue_links")
    op.drop_index("ix_commit_issue_links_issue_id", table_name="commit_issue_links")
    op.drop_index("ix_commit_issue_links_commit_id", table_name="commit_issue_links")
    op.drop_table("commit_issue_links")

    op.drop_index("ix_commit_pull_request_links_pr_number", table_name="commit_pull_request_links")
    op.drop_index(
        "ix_commit_pull_request_links_pull_request_id", table_name="commit_pull_request_links"
    )
    op.drop_index("ix_commit_pull_request_links_commit_id", table_name="commit_pull_request_links")
    op.drop_table("commit_pull_request_links")

    op.drop_column("issues", "html_url")
    op.drop_column("issues", "labels")

    op.drop_column("pull_requests", "html_url")
    op.drop_column("pull_requests", "labels")
    op.drop_column("pull_requests", "closed_at")
