"""add engineering documents and design constraints tables
Revision ID: 0005_add_engineering_context
Revises: 0004_add_pr_issue_links
Create Date: 2026-09-08 12:30:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "0005_add_engineering_context"
down_revision: str | None = "0004_add_pr_issue_links"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create engineering_docs table
    op.create_table(
        "engineering_docs",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "repository_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("path", sa.String(1024), nullable=False),
        sa.Column("doc_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(510), nullable=False),
        sa.Column("format", sa.String(50), nullable=False, server_default="markdown"),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="n/a"),
        sa.Column("deciders", sa.String(510), nullable=True),
        sa.Column("raw_content", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("extra_metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_engineering_docs_repository_id", "engineering_docs", ["repository_id"])
    op.create_index("ix_engineering_docs_path", "engineering_docs", ["path"])
    op.create_index("ix_engineering_docs_doc_type", "engineering_docs", ["doc_type"])

    # 2. Create design_constraints table
    op.create_table(
        "design_constraints",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "repository_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("repositories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("engineering_docs.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("level", sa.String(50), nullable=False, server_default="must"),
        sa.Column("title", sa.String(510), nullable=False),
        sa.Column("statement", sa.Text(), nullable=False),
        sa.Column("source_path", sa.String(1024), nullable=False),
        sa.Column("line_start", sa.Integer(), nullable=True),
        sa.Column("line_end", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("extra_metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_design_constraints_repository_id", "design_constraints", ["repository_id"])
    op.create_index("ix_design_constraints_document_id", "design_constraints", ["document_id"])
    op.create_index("ix_design_constraints_category", "design_constraints", ["category"])


def downgrade() -> None:
    op.drop_index("ix_design_constraints_category", table_name="design_constraints")
    op.drop_index("ix_design_constraints_document_id", table_name="design_constraints")
    op.drop_index("ix_design_constraints_repository_id", table_name="design_constraints")
    op.drop_table("design_constraints")

    op.drop_index("ix_engineering_docs_doc_type", table_name="engineering_docs")
    op.drop_index("ix_engineering_docs_path", table_name="engineering_docs")
    op.drop_index("ix_engineering_docs_repository_id", table_name="engineering_docs")
    op.drop_table("engineering_docs")
