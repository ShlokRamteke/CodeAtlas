"""add code_dependencies table

Revision ID: 0002_add_dependencies
Revises: 0001_initial_schema
Create Date: 2026-08-22 22:37:00.000000

"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_add_dependencies"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "code_dependencies",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "repository_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_file_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("source_files.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_path", sa.String(1024), nullable=False),
        sa.Column("target_path", sa.String(1024), nullable=False),
        sa.Column("imported_symbol", sa.String(255), nullable=True),
        sa.Column("kind", sa.String(50), nullable=False, server_default="internal"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_code_dependencies_repository_id", "code_dependencies", ["repository_id"])
    op.create_index("ix_code_dependencies_source_file_id", "code_dependencies", ["source_file_id"])
    op.create_index("ix_code_dependencies_source_path", "code_dependencies", ["source_path"])
    op.create_index("ix_code_dependencies_target_path", "code_dependencies", ["target_path"])


def downgrade() -> None:
    op.drop_index("ix_code_dependencies_target_path", table_name="code_dependencies")
    op.drop_index("ix_code_dependencies_source_path", table_name="code_dependencies")
    op.drop_index("ix_code_dependencies_source_file_id", table_name="code_dependencies")
    op.drop_index("ix_code_dependencies_repository_id", table_name="code_dependencies")
    op.drop_table("code_dependencies")
