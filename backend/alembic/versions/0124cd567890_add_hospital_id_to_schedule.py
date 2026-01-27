"""add hospital_id to schedule

Revision ID: 0124cd567890
Revises: 0123ab456789
Create Date: 2026-01-27 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0124cd567890"
down_revision: Union[str, None] = "0123ab456789"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Adiciona coluna hospital_id à tabela schedule.
    Campo opcional que permite associar uma escala a um hospital específico
    para exibir a cor do hospital nos cards.
    """
    # Adiciona coluna hospital_id (nullable)
    op.add_column(
        "schedule",
        sa.Column("hospital_id", sa.Integer(), nullable=True),
    )

    # Cria índice para consultas filtradas por hospital
    op.create_index(
        op.f("ix_schedule_hospital_id"),
        "schedule",
        ["hospital_id"],
        unique=False,
    )

    # Cria foreign key para hospital
    op.create_foreign_key(
        "fk_schedule_hospital_id",
        "schedule",
        "hospital",
        ["hospital_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """
    Remove coluna hospital_id da tabela schedule.
    """
    # Remove foreign key
    op.drop_constraint("fk_schedule_hospital_id", "schedule", type_="foreignkey")

    # Remove índice
    op.drop_index(op.f("ix_schedule_hospital_id"), table_name="schedule")

    # Remove coluna
    op.drop_column("schedule", "hospital_id")
