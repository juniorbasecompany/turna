"""add member can_peds sequence vacation

Revision ID: 0132rs901238
Revises: 0131pq901237
Create Date: 2026-02-01 14:00:00.000000

Adiciona campos can_peds (boolean), sequence (integer) e vacation (JSON) na tabela member.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0132rs901238"
down_revision: Union[str, None] = "0131pq901237"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Adiciona colunas can_peds, sequence e vacation na tabela member.
    """
    op.add_column(
        "member",
        sa.Column("can_peds", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "member",
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "member",
        sa.Column(
            "vacation",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    """
    Remove colunas can_peds, sequence e vacation da tabela member.
    """
    op.drop_column("member", "vacation")
    op.drop_column("member", "sequence")
    op.drop_column("member", "can_peds")
