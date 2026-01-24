"""make hospital prompt nullable

Revision ID: 0106qr789012
Revises: 0105op678901
Create Date: 2026-01-17 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0106qr789012"
down_revision: Union[str, None] = "0105op678901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tornar a coluna prompt nullable
    op.alter_column(
        "hospital",
        "prompt",
        existing_type=sa.String(),
        nullable=True,
    )


def downgrade() -> None:
    # Reverter: tornar prompt NOT NULL novamente
    # Primeiro, atualizar registros NULL para string vazia
    op.execute("UPDATE hospital SET prompt = '' WHERE prompt IS NULL")

    # Depois, tornar NOT NULL
    op.alter_column(
        "hospital",
        "prompt",
        existing_type=sa.String(),
        nullable=False,
    )
