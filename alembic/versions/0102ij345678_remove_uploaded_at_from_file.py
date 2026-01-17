"""remove uploaded_at from file table

Revision ID: 0102ij345678
Revises: 0101gh234567
Create Date: 2026-01-17 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0102ij345678"
down_revision: Union[str, None] = "0101gh234567"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove coluna uploaded_at da tabela file
    op.drop_column("file", "uploaded_at")


def downgrade() -> None:
    # Adiciona coluna uploaded_at de volta (com valores NULL, pois não há como recuperar os valores originais)
    op.add_column(
        "file",
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=True,  # Permite NULL no downgrade
        ),
    )
    # Preencher com created_at para registros existentes
    op.execute(
        sa.text("UPDATE file SET uploaded_at = created_at WHERE uploaded_at IS NULL")
    )
    # Tornar NOT NULL após preencher
    op.alter_column("file", "uploaded_at", nullable=False)