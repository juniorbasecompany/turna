"""remove profile table

Revision ID: 0121uv012345
Revises: 0120st012345
Create Date: 2026-01-22 05:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0121uv012345"
down_revision: Union[str, None] = "0120st012345"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove a tabela profile completamente.
    
    Passos:
    1. Remover índice único parcial (se existir)
    2. Remover constraint única
    3. Remover índices
    4. Remover foreign keys (serão removidas automaticamente com a tabela)
    5. Remover tabela
    """
    # 1. Remover índice único parcial (se existir)
    op.execute("DROP INDEX IF EXISTS uq_profile_tenant_member_no_hospital")
    op.execute("DROP INDEX IF EXISTS uq_profile_tenant_account_no_hospital")
    
    # 2. Remover constraint única (se existir)
    op.execute("ALTER TABLE profile DROP CONSTRAINT IF EXISTS uq_profile_tenant_member_hospital")
    op.execute("ALTER TABLE profile DROP CONSTRAINT IF EXISTS uq_profile_tenant_account_hospital")
    
    # 3. Remover índices
    op.execute("DROP INDEX IF EXISTS ix_profile_tenant_id")
    op.execute("DROP INDEX IF EXISTS ix_profile_member_id")
    op.execute("DROP INDEX IF EXISTS ix_profile_account_id")
    op.execute("DROP INDEX IF EXISTS ix_profile_hospital_id")
    
    # 4. Remover foreign keys (serão removidas automaticamente, mas vamos garantir)
    op.execute("ALTER TABLE profile DROP CONSTRAINT IF EXISTS profile_tenant_id_fkey")
    op.execute("ALTER TABLE profile DROP CONSTRAINT IF EXISTS profile_member_id_fkey")
    op.execute("ALTER TABLE profile DROP CONSTRAINT IF EXISTS profile_account_id_fkey")
    op.execute("ALTER TABLE profile DROP CONSTRAINT IF EXISTS profile_hospital_id_fkey")
    
    # 5. Remover tabela
    op.drop_table("profile")


def downgrade() -> None:
    """
    Recria a tabela profile (estrutura final após migrações).
    """
    # Criar tabela profile
    op.create_table(
        "profile",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("hospital_id", sa.Integer(), nullable=True),
        sa.Column("attribute", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.ForeignKeyConstraint(["member_id"], ["member.id"]),
        sa.ForeignKeyConstraint(["hospital_id"], ["hospital.id"]),
    )

    # Criar índices
    op.create_index(op.f("ix_profile_tenant_id"), "profile", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_profile_member_id"), "profile", ["member_id"], unique=False)
    op.create_index(op.f("ix_profile_hospital_id"), "profile", ["hospital_id"], unique=False)

    # Constraint única
    op.create_unique_constraint(
        "uq_profile_tenant_member_hospital",
        "profile",
        ["tenant_id", "member_id", "hospital_id"],
    )

    # Índice único parcial para garantir apenas um profile sem hospital
    op.execute("""
        CREATE UNIQUE INDEX uq_profile_tenant_member_no_hospital
        ON profile (tenant_id, member_id)
        WHERE hospital_id IS NULL
    """)
