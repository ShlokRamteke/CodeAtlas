"""add pr branches and touched files columns
Revision ID: 0006_add_pr_branches_and_touched_files
Revises: 0005_add_engineering_context
Create Date: 2026-09-16 16:15:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0006_add_pr_branches_and_touched_files"
down_revision: str | None = "0005_add_engineering_context"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("pull_requests", sa.Column("head_branch", sa.String(255), nullable=True))
    op.add_column("pull_requests", sa.Column("base_branch", sa.String(255), nullable=True))
    op.add_column(
        "pull_requests",
        sa.Column("touched_files", sa.JSON().with_variant(JSONB, "postgresql"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pull_requests", "touched_files")
    op.drop_column("pull_requests", "base_branch")
    op.drop_column("pull_requests", "head_branch")
