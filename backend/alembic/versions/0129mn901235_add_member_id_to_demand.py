"""add member_id to demand

Revision ID: 0129mn901235
Revises: 0128kl890124
Create Date: 2026-01-29 12:00:00.000000

Campo demand.member_id: member atribuído à demanda no momento do cálculo da escala.
ON DELETE RESTRICT, aceita null.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0129mn901235"
down_revision: Union[str, None] = "0128kl890124"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("demand", sa.Column("member_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_demand_member_id"), "demand", ["member_id"], unique=False)
    op.create_foreign_key(
        "fk_demand_member_id",
        "demand",
        "member",
        ["member_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_demand_member_id", "demand", type_="foreignkey")
    op.drop_index(op.f("ix_demand_member_id"), table_name="demand")
    op.drop_column("demand", "member_id")
