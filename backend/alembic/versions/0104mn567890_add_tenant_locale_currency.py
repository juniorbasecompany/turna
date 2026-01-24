"""add tenant locale and currency, update timezone default

Revision ID: 0104mn567890
Revises: 0103kl456789
Create Date: 2026-01-17 01:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0104mn567890"
down_revision: Union[str, None] = "0103kl456789"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adicionar colunas locale e currency
    op.add_column(
        "tenant",
        sa.Column("locale", sa.String(), nullable=False, server_default="pt-BR"),
    )
    op.add_column(
        "tenant",
        sa.Column("currency", sa.String(), nullable=False, server_default="BRL"),
    )

    # Atualizar default de timezone para America/Sao_Paulo (backfill para tenants existentes)
    # Primeiro atualizar tenants que têm UTC para America/Sao_Paulo
    op.execute(
        sa.text("UPDATE tenant SET timezone = 'America/Sao_Paulo' WHERE timezone = 'UTC'")
    )

    # Remover o server_default antigo e adicionar o novo
    op.alter_column("tenant", "timezone", server_default="America/Sao_Paulo")


def downgrade() -> None:
    # Reverter default de timezone para UTC (mas não alterar valores existentes)
    op.alter_column("tenant", "timezone", server_default="UTC")

    # Remover colunas locale e currency
    op.drop_column("tenant", "currency")
    op.drop_column("tenant", "locale")
