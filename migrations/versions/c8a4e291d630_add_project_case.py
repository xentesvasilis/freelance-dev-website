"""Add private project cases without modifying existing records.

Revision ID: c8a4e291d630
Revises: 784018745121
"""
from alembic import op
import sqlalchemy as sa

revision = "c8a4e291d630"
down_revision = "784018745121"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "project_case",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(64), nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("client_name", sa.String(120), nullable=False),
        sa.Column("client_email", sa.String(254), nullable=False),
        sa.Column("client_phone", sa.String(40)),
        sa.Column("company", sa.String(160)),
        sa.Column("industry", sa.String(120)),
        sa.Column("project_summary", sa.Text(), nullable=False),
        sa.Column("internal_notes", sa.Text()),
        sa.Column("package_name", sa.String(120)),
        sa.Column("quoted_price_cents", sa.Integer()),
        sa.Column("currency", sa.String(3), nullable=False, server_default="EUR"),
        sa.Column("status", sa.String(30), nullable=False, server_default="proposal"),
        sa.Column("priority", sa.String(10), nullable=False, server_default="normal"),
        sa.Column("target_start_date", sa.Date()),
        sa.Column("target_delivery_date", sa.Date()),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("development_started_at", sa.DateTime(timezone=True)),
        sa.Column("testing_started_at", sa.DateTime(timezone=True)),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("maintenance_started_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["lead_id"], ["lead.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("lead_id"),
        sa.UniqueConstraint("public_id"),
        sa.CheckConstraint("status IN ('proposal','proposal_sent','accepted','in_development','waiting_for_client','testing','delivered','maintenance','on_hold','cancelled')", name="valid_project_status"),
        sa.CheckConstraint("priority IN ('low','normal','high','urgent')", name="valid_project_priority"),
        sa.CheckConstraint("quoted_price_cents IS NULL OR quoted_price_cents >= 0", name="nonnegative_project_price"),
        sa.CheckConstraint("currency = 'EUR'", name="project_currency_eur"),
        sa.CheckConstraint("target_delivery_date IS NULL OR target_start_date IS NULL OR target_delivery_date >= target_start_date", name="valid_project_dates"),
    )
    for column in ("industry", "status", "priority", "target_delivery_date", "updated_at"):
        op.create_index("ix_project_case_" + column, "project_case", [column])


def downgrade():
    # Explicit rollback loses project records only. Back up before invoking it.
    op.drop_table("project_case")
