"""make schedule hospital_id required with ON DELETE RESTRICT

Revision ID: 0125ef678901
Revises: 0124cd567890
Create Date: 2026-01-27 14:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0125ef678901"
down_revision: Union[str, None] = "0124cd567890"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Altera hospital_id em schedule:
    - Remove FK existente (se houver)
    - Torna a coluna NOT NULL
    - Cria nova FK com ON DELETE RESTRICT
    """
    # Remove FK existente (criada na migração anterior)
    op.drop_constraint("fk_schedule_hospital_id", "schedule", type_="foreignkey")

    # Torna a coluna NOT NULL
    op.alter_column(
        "schedule",
        "hospital_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    # Cria FK com ON DELETE RESTRICT
    op.create_foreign_key(
        "fk_schedule_hospital_id",
        "schedule",
        "hospital",
        ["hospital_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    """
    Reverte para hospital_id nullable com ON DELETE SET NULL.
    """
    # Remove FK com RESTRICT
    op.drop_constraint("fk_schedule_hospital_id", "schedule", type_="foreignkey")

    # Torna a coluna nullable novamente
    op.alter_column(
        "schedule",
        "hospital_id",
        existing_type=sa.Integer(),
        nullable=True,
    )

    # Recria FK com ON DELETE SET NULL
    op.create_foreign_key(
        "fk_schedule_hospital_id",
        "schedule",
        "hospital",
        ["hospital_id"],
        ["id"],
        ondelete="SET NULL",
    )
