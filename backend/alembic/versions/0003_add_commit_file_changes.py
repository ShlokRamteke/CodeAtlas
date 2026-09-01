"""add commit_file_changes table and commit stats
Revision ID: 0003_add_commit_file_changes
Revises: 0002_add_dependencies
Create Date: 2026-08-25 16:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0003_add_commit_file_changes"
down_revision: str | None = "0002_add_dependencies"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add stats columns to commits if not existing
    op.add_column("commits", sa.Column("parent_hashes", JSONB, nullable=True))
    op.add_column(
        "commits",
        sa.Column("files_changed_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "commits", sa.Column("insertions", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "commits", sa.Column("deletions", sa.Integer(), nullable=False, server_default="0")
    )

    # Create commit_file_changes table
    op.create_table(
        "commit_file_changes",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "commit_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("commits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_path", sa.String(1024), nullable=False),
        sa.Column("change_type", sa.String(50), nullable=False, server_default="modified"),
        sa.Column("insertions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deletions", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("old_path", sa.String(1024), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_commit_file_changes_commit_id", "commit_file_changes", ["commit_id"])
    op.create_index("ix_commit_file_changes_file_path", "commit_file_changes", ["file_path"])


def downgrade() -> None:
    op.drop_index("ix_commit_file_changes_file_path", table_name="commit_file_changes")
    op.drop_index("ix_commit_file_changes_commit_id", table_name="commit_file_changes")
    op.drop_table("commit_file_changes")

    op.drop_column("commits", "deletions")
    op.drop_column("commits", "insertions")
    op.drop_column("commits", "files_changed_count")
    op.drop_column("commits", "parent_hashes")
