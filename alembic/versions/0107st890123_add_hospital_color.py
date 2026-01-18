"""add hospital color

Revision ID: 0107st890123
Revises: 0106qr789012
Create Date: 2026-01-17 14:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0107st890123"
down_revision: Union[str, None] = "0106qr789012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adicionar coluna color (nullable, string para hexadecimal)
    op.add_column(
        "hospital",
        sa.Column("color", sa.String(), nullable=True),
    )


def downgrade() -> None:
    # Remover coluna color
    op.drop_column("hospital", "color")
