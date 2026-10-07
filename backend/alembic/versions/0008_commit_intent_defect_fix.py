"""add commit intent and defect fix columns
Revision ID: 0008_commit_intent_defect_fix
Revises: 0007_symbol_arch_role
Create Date: 2026-10-07 14:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_commit_intent_defect_fix"
down_revision: str | None = "0007_symbol_arch_role"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("commits", sa.Column("commit_intent", sa.String(50), nullable=True))
    op.add_column(
        "commits",
        sa.Column(
            "is_defect_fix",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_index(
        op.f("ix_commits_commit_intent"),
        "commits",
        ["commit_intent"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commits_is_defect_fix"),
        "commits",
        ["is_defect_fix"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_commits_is_defect_fix"), table_name="commits")
    op.drop_index(op.f("ix_commits_commit_intent"), table_name="commits")
    op.drop_column("commits", "is_defect_fix")
    op.drop_column("commits", "commit_intent")
