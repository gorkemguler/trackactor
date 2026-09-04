"""users, sessions, audit log, and case ownership columns (v0.4)

Revision ID: 0002_users_audit
Revises: 0001_baseline
Create Date: 2026-09-04
"""

import sqlalchemy as sa

from alembic import op

revision = "0002_users_audit"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None

_DT = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("username", sa.String(60), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(120)),
        sa.Column("is_admin", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("disabled", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", _DT, nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"])

    op.create_table(
        "sessions",
        sa.Column("token", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", _DT, nullable=False),
        sa.Column("expires_at", _DT, nullable=False),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("at", _DT, nullable=False),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("user_label", sa.String(120), nullable=False, server_default="anon"),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("entity_type", sa.String(30), nullable=False),
        sa.Column("entity_id", sa.Integer),
        sa.Column("summary", sa.String(255), nullable=False, server_default=""),
        sa.Column("changes", sa.JSON, nullable=False),
    )
    op.create_index("ix_audit_events_at", "audit_events", ["at"])
    op.create_index("ix_audit_events_entity_type", "audit_events", ["entity_type"])
    op.create_index("ix_audit_events_entity_id", "audit_events", ["entity_id"])

    # Plain columns - SQLite doesn't enforce FKs and batch-adding a named
    # constraint here is more trouble than it's worth. The ORM model carries
    # the ForeignKey, which is what relationship resolution uses.
    op.add_column("cases", sa.Column("assignee_id", sa.Integer))
    op.add_column("cases", sa.Column("created_by_id", sa.Integer))


def downgrade() -> None:
    with op.batch_alter_table("cases") as b:
        b.drop_column("created_by_id")
        b.drop_column("assignee_id")
    op.drop_table("audit_events")
    op.drop_table("sessions")
    op.drop_table("users")
