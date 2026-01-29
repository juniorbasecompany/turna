"""add schedule fields to demand

Revision ID: 0127ij789013
Revises: 0126gh789012
Create Date: 2026-01-28 12:00:00.000000

Campos de escala migrados de Schedule para Demand (fusão 1:1).
Não inclui period_start_at/period_end_at (período fica em job.input_data).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0127ij789013"
down_revision: Union[str, None] = "0126gh789012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enum para status da escala na Demand (PostgreSQL)
    demand_schedule_status = postgresql.ENUM("DRAFT", "PUBLISHED", "ARCHIVED", name="demand_schedule_status")
    demand_schedule_status.create(op.get_bind(), checkfirst=True)
    op.add_column("demand", sa.Column("schedule_status", postgresql.ENUM("DRAFT", "PUBLISHED", "ARCHIVED", name="demand_schedule_status", create_type=False), nullable=True))
    op.add_column("demand", sa.Column("schedule_name", sa.String(), nullable=True))
    op.add_column("demand", sa.Column("schedule_version_number", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("demand", sa.Column("pdf_file_id", sa.Integer(), nullable=True))
    op.add_column("demand", sa.Column("schedule_result_data", postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column("demand", sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("demand", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))

    op.create_index(op.f("ix_demand_schedule_status"), "demand", ["schedule_status"], unique=False)
    op.create_index(op.f("ix_demand_pdf_file_id"), "demand", ["pdf_file_id"], unique=False)
    op.create_foreign_key("fk_demand_pdf_file_id", "demand", "file", ["pdf_file_id"], ["id"], ondelete="SET NULL")


def downgrade() -> None:
    op.drop_constraint("fk_demand_pdf_file_id", "demand", type_="foreignkey")
    op.drop_index(op.f("ix_demand_pdf_file_id"), table_name="demand")
    op.drop_index(op.f("ix_demand_schedule_status"), table_name="demand")
    op.drop_column("demand", "published_at")
    op.drop_column("demand", "generated_at")
    op.drop_column("demand", "schedule_result_data")
    op.drop_column("demand", "pdf_file_id")
    op.drop_column("demand", "schedule_version_number")
    op.drop_column("demand", "schedule_name")
    op.drop_column("demand", "schedule_status")
    postgresql.ENUM("DRAFT", "PUBLISHED", "ARCHIVED", name="demand_schedule_status").drop(op.get_bind(), checkfirst=True)
