"""baseline schema (v0.3)

Creates every table as it stood at v0.3. Guarded so that adopting a database
that was built with the old create_all path is a no-op - it just gets stamped.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-04
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None

_DT = sa.DateTime(timezone=True)


def _exists(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def upgrade() -> None:
    if _exists("actors"):
        return  # pre-alembic database - already at this schema

    op.create_table(
        "actors",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, unique=True),
        sa.Column("actor_type", sa.String(40), nullable=False, server_default="unknown"),
        sa.Column("aliases", sa.JSON, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("tlp", sa.String(10), nullable=False, server_default="AMBER"),
        sa.Column("first_seen", _DT),
        sa.Column("last_seen", _DT),
        sa.Column("created_at", _DT, nullable=False),
        sa.Column("updated_at", _DT, nullable=False),
    )
    op.create_index("ix_actors_name", "actors", ["name"])

    op.create_table(
        "contacts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("actor_id", sa.Integer, sa.ForeignKey("actors.id", ondelete="CASCADE")),
        sa.Column("channel_type", sa.String(30), nullable=False, server_default="other"),
        sa.Column("value", sa.String(500), nullable=False),
        sa.Column("normalized", sa.String(500), nullable=False, server_default=""),
        sa.Column("label", sa.String(255)),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("notes", sa.Text),
        sa.Column("last_seen", _DT),
        sa.Column("created_at", _DT, nullable=False),
    )
    op.create_index("ix_contacts_normalized", "contacts", ["normalized"])

    op.create_table(
        "cases",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.String(120), nullable=False, unique=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("source_platform", sa.String(60), nullable=False, server_default="Manual"),
        sa.Column("source_url", sa.String(500)),
        sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("analyst", sa.String(120)),
        sa.Column("objective", sa.Text),
        sa.Column("tags", sa.JSON, nullable=False),
        sa.Column("created_at", _DT, nullable=False),
        sa.Column("updated_at", _DT, nullable=False),
    )
    op.create_index("ix_cases_case_id", "cases", ["case_id"])
    op.create_index("ix_cases_status", "cases", ["status"])

    op.create_table(
        "case_actors",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.Integer, sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", sa.Integer, sa.ForeignKey("actors.id", ondelete="CASCADE"), nullable=False),
        sa.Column("note", sa.Text),
        sa.Column("created_at", _DT, nullable=False),
        sa.UniqueConstraint("case_id", "actor_id", name="uq_case_actor"),
    )

    op.create_table(
        "case_contacts",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.Integer, sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", sa.Integer, sa.ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("outreach_handle", sa.String(255)),
        sa.Column("note", sa.Text),
        sa.Column("created_at", _DT, nullable=False),
        sa.UniqueConstraint("case_id", "contact_id", name="uq_case_contact"),
    )

    op.create_table(
        "interactions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("case_id", sa.Integer, sa.ForeignKey("cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contact_id", sa.Integer, sa.ForeignKey("contacts.id", ondelete="SET NULL")),
        sa.Column("direction", sa.String(10), nullable=False, server_default="outbound"),
        sa.Column("occurred_at", _DT, nullable=False),
        sa.Column("summary", sa.Text, nullable=False),
        sa.Column("analyst", sa.String(120)),
        sa.Column("created_at", _DT, nullable=False),
    )
    op.create_index("ix_interactions_occurred_at", "interactions", ["occurred_at"])

    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("prefix", sa.String(16), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("scope", sa.String(10), nullable=False, server_default="read"),
        sa.Column("revoked", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("last_used_at", _DT),
        sa.Column("created_at", _DT, nullable=False),
    )
    op.create_index("ix_api_keys_prefix", "api_keys", ["prefix"])
    op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"])

    op.create_table(
        "webhooks",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("secret", sa.String(120), nullable=False),
        sa.Column("events", sa.JSON, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("last_status", sa.Integer),
        sa.Column("last_attempt_at", _DT),
        sa.Column("failure_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", _DT, nullable=False),
    )


def downgrade() -> None:
    for table in (
        "webhooks",
        "api_keys",
        "interactions",
        "case_contacts",
        "case_actors",
        "cases",
        "contacts",
        "actors",
    ):
        op.drop_table(table)
