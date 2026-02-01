"""make demand.hospital_id required

Revision ID: 0131pq901237
Revises: 0130op901236
Create Date: 2026-02-01 12:00:00.000000

Torna hospital_id obrigatório na tabela demand (NOT NULL).
A tabela demand está zerada; não há valores NULL a tratar.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0131pq901237"
down_revision: Union[str, None] = "0130op901236"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "demand",
        "hospital_id",
        existing_type=sa.Integer(),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "demand",
        "hospital_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
