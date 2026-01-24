"""add account_id to professional

Revision ID: 0111ab012345
Revises: 0110yz012345
Create Date: 2026-01-18 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0111ab012345"
down_revision: Union[str, None] = "0110yz012345"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adicionar coluna account_id (nullable=True para permitir profissionais sem account)
    op.add_column(
        "professional",
        sa.Column("account_id", sa.Integer(), nullable=True)
    )

    # Criar foreign key para account
    op.create_foreign_key(
        "fk_professional_account_id",
        "professional",
        "account",
        ["account_id"],
        ["id"]
    )

    # Criar índice para account_id
    op.create_index(
        op.f("ix_professional_account_id"),
        "professional",
        ["account_id"],
        unique=False
    )


def downgrade() -> None:
    # Remover índice
    op.drop_index(op.f("ix_professional_account_id"), table_name="professional")

    # Remover foreign key
    op.drop_constraint("fk_professional_account_id", "professional", type_="foreignkey")

    # Remover coluna
    op.drop_column("professional", "account_id")
