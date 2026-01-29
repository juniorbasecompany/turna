"""drop schedule table

Revision ID: 0128kl890124
Revises: 0127ij789013
Create Date: 2026-01-28 12:10:00.000000

Remove tabela schedule; estado da escala está em demand.
Tabela schedule está vazia (sem migração de dados).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0128kl890124"
down_revision: Union[str, None] = "0127ij789013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("schedule")


def downgrade() -> None:
    # Recriar tabela schedule (estrutura mínima para rollback)
    op.execute("CREATE TYPE schedule_status AS ENUM ('DRAFT', 'PUBLISHED', 'ARCHIVED')")
    op.create_table(
        "schedule",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("demand_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("period_start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", postgresql.ENUM("DRAFT", "PUBLISHED", "ARCHIVED", name="schedule_status", create_type=False), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("pdf_file_id", sa.Integer(), nullable=True),
        sa.Column("result_data", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.ForeignKeyConstraint(["demand_id"], ["demand.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["job.id"]),
        sa.ForeignKeyConstraint(["pdf_file_id"], ["file.id"]),
    )
    op.create_index(op.f("ix_schedule_tenant_id"), "schedule", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_schedule_demand_id"), "schedule", ["demand_id"], unique=True)
    op.create_index(op.f("ix_schedule_job_id"), "schedule", ["job_id"], unique=False)
    op.create_index(op.f("ix_schedule_pdf_file_id"), "schedule", ["pdf_file_id"], unique=False)
    op.create_index(op.f("ix_schedule_status"), "schedule", ["status"], unique=False)
