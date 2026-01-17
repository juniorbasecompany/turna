"""remove updated_at from file table

Revision ID: 0103kl456789
Revises: 0102ij345678
Create Date: 2026-01-17 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0103kl456789"
down_revision: Union[str, None] = "0102ij345678"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove coluna updated_at da tabela file
    op.drop_column("file", "updated_at")


def downgrade() -> None:
    # Adiciona coluna updated_at de volta (com valores NULL)
    op.add_column(
        "file",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,  # Permite NULL no downgrade
        ),
    )
    # Preencher com created_at para registros existentes
    op.execute(
        sa.text("UPDATE file SET updated_at = created_at WHERE updated_at IS NULL")
    )
    # Tornar NOT NULL após preencher
    op.alter_column("file", "updated_at", nullable=False)
