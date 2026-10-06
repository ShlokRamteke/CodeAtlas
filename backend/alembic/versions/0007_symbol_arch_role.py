"""add symbol architectural role column
Revision ID: 0007_symbol_arch_role
Revises: 0006_pr_branches_files
Create Date: 2026-10-06 19:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_symbol_arch_role"
down_revision: str | None = "0006_pr_branches_files"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("symbols", sa.Column("architectural_role", sa.String(50), nullable=True))
    op.create_index(
        op.f("ix_symbols_architectural_role"),
        "symbols",
        ["architectural_role"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_symbols_architectural_role"), table_name="symbols")
    op.drop_column("symbols", "architectural_role")
