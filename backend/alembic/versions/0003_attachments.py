"""evidence attachments (v0.6)

Revision ID: 0003_attachments
Revises: 0002_users_audit
Create Date: 2026-09-04
"""

import sqlalchemy as sa

from alembic import op

revision = "0003_attachments"
down_revision = "0002_users_audit"
branch_labels = None
depends_on = None

_DT = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "attachments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.Integer, sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("interaction_id", sa.Integer, sa.ForeignKey("interactions.id", ondelete="SET NULL")),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False, server_default="application/octet-stream"),
        sa.Column("size", sa.Integer, nullable=False, server_default="0"),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("tlp", sa.String(10), nullable=False, server_default="AMBER"),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column("uploaded_by_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", _DT, nullable=False),
    )
    op.create_index("ix_attachments_case_id", "attachments", ["case_id"])
    op.create_index("ix_attachments_sha256", "attachments", ["sha256"])


def downgrade() -> None:
    op.drop_table("attachments")
