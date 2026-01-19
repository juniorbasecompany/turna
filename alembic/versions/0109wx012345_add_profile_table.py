"""add profile table

Revision ID: 0109wx012345
Revises: 0108uv901234
Create Date: 2026-01-18 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0109wx012345"
down_revision: Union[str, None] = "0108uv901234"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Criar tabela profile
    op.create_table(
        "profile",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("hospital_id", sa.Integer(), nullable=True),
        sa.Column("attribute", postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.ForeignKeyConstraint(["account_id"], ["account.id"]),
        sa.ForeignKeyConstraint(["hospital_id"], ["hospital.id"]),
    )

    # Criar índices
    op.create_index(op.f("ix_profile_tenant_id"), "profile", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_profile_account_id"), "profile", ["account_id"], unique=False)
    op.create_index(op.f("ix_profile_hospital_id"), "profile", ["hospital_id"], unique=False)

    # Constraint única: um account pode ter apenas um profile por (tenant_id, hospital_id)
    # Isso garante:
    # - Um account pode ter apenas um profile "geral" (sem hospital) por tenant
    # - Um account pode ter apenas um profile por hospital específico por tenant
    #
    # Nota: No PostgreSQL, NULLs são tratados de forma especial em constraints únicas.
    # Para garantir que só haja um profile sem hospital, usamos um índice único parcial.
    # Primeiro, criamos a constraint para hospital_id não-nulo:
    op.create_unique_constraint(
        "uq_profile_tenant_account_hospital",
        "profile",
        ["tenant_id", "account_id", "hospital_id"],
    )

    # Depois, criamos um índice único parcial para garantir apenas um profile sem hospital:
    op.execute("""
        CREATE UNIQUE INDEX uq_profile_tenant_account_no_hospital
        ON profile (tenant_id, account_id)
        WHERE hospital_id IS NULL
    """)


def downgrade() -> None:
    # Remover índice único parcial
    op.execute("DROP INDEX IF EXISTS uq_profile_tenant_account_no_hospital")

    # Remover constraint única
    op.drop_constraint("uq_profile_tenant_account_hospital", "profile", type_="unique")

    # Remover índices
    op.drop_index(op.f("ix_profile_hospital_id"), table_name="profile")
    op.drop_index(op.f("ix_profile_account_id"), table_name="profile")
    op.drop_index(op.f("ix_profile_tenant_id"), table_name="profile")

    # Remover tabela
    op.drop_table("profile")
