"""make professional email required

Revision ID: 0112cd012345
Revises: 0111ab012345
Create Date: 2026-01-18 13:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0112cd012345"
down_revision: Union[str, None] = "0111ab012345"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tornar email obrigatório (nullable=False)
    # Como a tabela está vazia, podemos fazer diretamente
    op.alter_column(
        "professional",
        "email",
        existing_type=sa.String(),
        nullable=False
    )


def downgrade() -> None:
    # Reverter para nullable=True
    op.alter_column(
        "professional",
        "email",
        existing_type=sa.String(),
        nullable=True
    )
