"""add demand table

Revision ID: 0108uv901234
Revises: 0107st890123
Create Date: 2026-01-17 16:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0108uv901234"
down_revision: Union[str, None] = "0107st890123"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Criar tabela demand
    op.create_table(
        "demand",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("hospital_id", sa.Integer(), nullable=True),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("room", sa.String(), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("procedure", sa.String(), nullable=False),
        sa.Column("anesthesia_type", sa.String(), nullable=True),
        sa.Column("complexity", sa.String(), nullable=True),
        sa.Column("skills", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("priority", sa.String(), nullable=True),
        sa.Column("is_pediatric", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.ForeignKeyConstraint(["hospital_id"], ["hospital.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["job.id"]),
        sa.CheckConstraint("end_time > start_time", name="ck_demand_end_after_start"),
    )

    # Criar índices
    op.create_index(op.f("ix_demand_tenant_id"), "demand", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_demand_hospital_id"), "demand", ["hospital_id"], unique=False)
    op.create_index(op.f("ix_demand_job_id"), "demand", ["job_id"], unique=False)
    op.create_index(op.f("ix_demand_start_time"), "demand", ["start_time"], unique=False)
    op.create_index(op.f("ix_demand_end_time"), "demand", ["end_time"], unique=False)
    op.create_index(op.f("ix_demand_is_pediatric"), "demand", ["is_pediatric"], unique=False)

    # Índice composto para consultas comuns (tenant + período)
    op.create_index(
        "ix_demand_tenant_start_time",
        "demand",
        ["tenant_id", "start_time"],
        unique=False,
    )


def downgrade() -> None:
    # Remover índices
    op.drop_index("ix_demand_tenant_start_time", table_name="demand")
    op.drop_index(op.f("ix_demand_is_pediatric"), table_name="demand")
    op.drop_index(op.f("ix_demand_end_time"), table_name="demand")
    op.drop_index(op.f("ix_demand_start_time"), table_name="demand")
    op.drop_index(op.f("ix_demand_job_id"), table_name="demand")
    op.drop_index(op.f("ix_demand_hospital_id"), table_name="demand")
    op.drop_index(op.f("ix_demand_tenant_id"), table_name="demand")

    # Remover tabela
    op.drop_table("demand")
