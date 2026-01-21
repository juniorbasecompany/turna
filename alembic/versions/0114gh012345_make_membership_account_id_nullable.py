"""make membership account_id nullable and add email field

Revision ID: 0114gh012345
Revises: 0113ef012345
Create Date: 2026-01-21 07:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0114gh012345"
down_revision: Union[str, None] = "0113ef012345"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adicionar campo email em membership (para identificar convites pendentes)
    op.add_column(
        "membership",
        sa.Column("email", sa.String(), nullable=True)
    )

    # Preencher email dos memberships existentes a partir do account
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE membership
        SET email = account.email
        FROM account
        WHERE membership.account_id = account.id
          AND membership.email IS NULL
    """))

    # Remover constraint única antiga (tenant_id, account_id)
    op.drop_constraint("uq_membership_tenant_account", "membership", type_="unique")

    # Tornar account_id nullable
    op.alter_column(
        "membership",
        "account_id",
        existing_type=sa.Integer(),
        nullable=True
    )

    # Criar nova constraint única:
    # - Para account_id NOT NULL: (tenant_id, account_id) deve ser único
    # - Para account_id NULL: permitir múltiplos, mas usar (tenant_id, email) como identificador único
    # PostgreSQL permite múltiplos NULLs em UNIQUE, mas precisamos garantir unicidade por email quando account_id é NULL
    # Vamos criar um índice parcial único para (tenant_id, email) quando account_id IS NULL
    op.create_index(
        "ix_membership_tenant_email_pending",
        "membership",
        ["tenant_id", "email"],
        unique=True,
        postgresql_where=sa.text("account_id IS NULL")
    )

    # Recriar constraint única para (tenant_id, account_id) quando account_id não é NULL
    # Usando índice parcial único
    op.create_index(
        "ix_membership_tenant_account_active",
        "membership",
        ["tenant_id", "account_id"],
        unique=True,
        postgresql_where=sa.text("account_id IS NOT NULL")
    )


def downgrade() -> None:
    # Remover índices parciais únicos
    op.drop_index("ix_membership_tenant_account_active", table_name="membership")
    op.drop_index("ix_membership_tenant_email_pending", table_name="membership")

    # Tornar account_id NOT NULL novamente
    # Primeiro, garantir que não há account_id NULL
    conn = op.get_bind()
    conn.execute(sa.text("""
        DELETE FROM membership
        WHERE account_id IS NULL
    """))

    op.alter_column(
        "membership",
        "account_id",
        existing_type=sa.Integer(),
        nullable=False
    )

    # Recriar constraint única original
    op.create_unique_constraint(
        "uq_membership_tenant_account",
        "membership",
        ["tenant_id", "account_id"]
    )

    # Remover campo email
    op.drop_column("membership", "email")
