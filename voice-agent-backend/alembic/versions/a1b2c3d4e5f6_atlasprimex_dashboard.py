"""atlasprimex_dashboard — additive columns + holidays/ops_alerts/ops_tickets

Phase 4 of the AtlasPrimeX build. Purely additive and non-destructive: new nullable
columns and three new tables. No existing column is altered, retyped, or dropped, so the
live voice agent is unaffected.

NOTE: the running app applies these same changes at startup via
`app.db.database.ensure_columns()` (idempotent `ADD COLUMN IF NOT EXISTS`) and
`Base.metadata.create_all` (new tables). This revision mirrors that for teams using
`alembic upgrade head`.

Revision ID: a1b2c3d4e5f6
Revises: dcf429255ab1
Create Date: 2026-07-18 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "dcf429255ab1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Additive nullable columns.
    op.add_column("tenants", sa.Column("closed_greeting", sa.Text(), nullable=True))
    op.add_column("services", sa.Column("category", sa.String(), nullable=True))
    op.add_column("services", sa.Column("details", sa.JSON(), nullable=True))
    op.add_column("leads", sa.Column("email", sa.String(), nullable=True))
    op.add_column("users", sa.Column("title", sa.String(), nullable=True))

    # New tables.
    op.create_table(
        "holidays",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("date", sa.String(), nullable=True),
        sa.Column("closed", sa.Boolean(), nullable=True),
        sa.Column("hours", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ops_alerts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("severity", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=True),
        sa.Column("merchant_name", sa.String(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "ops_tickets",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=True),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=True),
        sa.Column("merchant_name", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("priority", sa.String(), nullable=True),
        sa.Column("assignee", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("ops_tickets")
    op.drop_table("ops_alerts")
    op.drop_table("holidays")
    op.drop_column("users", "title")
    op.drop_column("leads", "email")
    op.drop_column("services", "details")
    op.drop_column("services", "category")
    op.drop_column("tenants", "closed_greeting")
