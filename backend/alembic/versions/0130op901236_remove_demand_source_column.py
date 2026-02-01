"""remove demand.source column

Revision ID: 0130op901236
Revises: 0129mn901235
Create Date: 2026-02-01 12:00:00.000000

Remove a coluna source da tabela demand (campo redundante e não utilizado).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "0130op901236"
down_revision: Union[str, None] = "0129mn901235"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("demand", "source")


def downgrade() -> None:
    op.add_column(
        "demand",
        sa.Column(
            "source",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
        ),
    )
