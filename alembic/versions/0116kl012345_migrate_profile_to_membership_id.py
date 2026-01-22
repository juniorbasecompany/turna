"""migrate profile account_id to membership_id

Revision ID: 0116kl012345
Revises: 0115ij012345
Create Date: 2026-01-21 09:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0116kl012345"
down_revision: Union[str, None] = "0115ij012345"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Migra Profile de account_id para membership_id.
    
    Passos:
    1. Adicionar coluna membership_id (nullable temporariamente)
    2. Preencher membership_id a partir de account_id (via Membership)
    3. Remover constraint única antiga (tenant_id, account_id, hospital_id)
    4. Remover coluna account_id
    5. Tornar membership_id NOT NULL
    6. Criar constraint única nova (tenant_id, membership_id, hospital_id)
    7. Criar foreign key para membership.id
    8. Criar índice em membership_id
    """
    conn = op.get_bind()
    
    # 1. Adicionar coluna membership_id (nullable temporariamente)
    op.add_column(
        "profile",
        sa.Column("membership_id", sa.Integer(), nullable=True)
    )
    
    # 2. Preencher membership_id a partir de account_id (via Membership)
    # Para cada profile, encontrar o membership ACTIVE correspondente
    conn.execute(sa.text("""
        UPDATE profile
        SET membership_id = membership.id
        FROM membership
        WHERE profile.account_id = membership.account_id
          AND profile.tenant_id = membership.tenant_id
          AND membership.status = 'ACTIVE'
    """))
    
    # Verificar se há profiles sem membership (devem ser removidos ou tratados)
    orphan_count = conn.execute(sa.text("""
        SELECT COUNT(*)
        FROM profile
        WHERE membership_id IS NULL
    """)).scalar()
    
    if int(orphan_count or 0) > 0:
        # Remover profiles órfãos (sem membership ACTIVE correspondente)
        conn.execute(sa.text("""
            DELETE FROM profile
            WHERE membership_id IS NULL
        """))
    
    # 3. Remover índice único parcial antigo
    op.execute("DROP INDEX IF EXISTS uq_profile_tenant_account_no_hospital")
    
    # 4. Remover constraint única antiga
    op.drop_constraint("uq_profile_tenant_account_hospital", "profile", type_="unique")
    
    # 5. Remover foreign key e índice de account_id
    op.drop_index(op.f("ix_profile_account_id"), table_name="profile")
    op.drop_constraint("profile_account_id_fkey", "profile", type_="foreignkey")
    
    # 6. Remover coluna account_id
    op.drop_column("profile", "account_id")
    
    # 7. Tornar membership_id NOT NULL
    op.alter_column(
        "profile",
        "membership_id",
        existing_type=sa.Integer(),
        nullable=False
    )
    
    # 8. Criar foreign key para membership.id
    op.create_foreign_key(
        "profile_membership_id_fkey",
        "profile",
        "membership",
        ["membership_id"],
        ["id"]
    )
    
    # 9. Criar índice em membership_id
    op.create_index(
        op.f("ix_profile_membership_id"),
        "profile",
        ["membership_id"],
        unique=False
    )
    
    # 9. Criar constraint única nova (tenant_id, membership_id, hospital_id)
    op.create_unique_constraint(
        "uq_profile_tenant_membership_hospital",
        "profile",
        ["tenant_id", "membership_id", "hospital_id"]
    )
    
    # 10. Criar índice único parcial para garantir apenas um profile sem hospital por membership
    op.execute("""
        CREATE UNIQUE INDEX uq_profile_tenant_membership_no_hospital
        ON profile (tenant_id, membership_id)
        WHERE hospital_id IS NULL
    """)


def downgrade() -> None:
    """
    Reverter migração: membership_id -> account_id
    """
    conn = op.get_bind()
    
    # 1. Adicionar coluna account_id (nullable temporariamente)
    op.add_column(
        "profile",
        sa.Column("account_id", sa.Integer(), nullable=True)
    )
    
    # 2. Preencher account_id a partir de membership_id (via Membership)
    conn.execute(sa.text("""
        UPDATE profile
        SET account_id = membership.account_id
        FROM membership
        WHERE profile.membership_id = membership.id
    """))
    
    # Remover profiles sem account_id (se houver)
    conn.execute(sa.text("""
        DELETE FROM profile
        WHERE account_id IS NULL
    """))
    
    # 3. Remover índice único parcial
    op.execute("DROP INDEX IF EXISTS uq_profile_tenant_membership_no_hospital")
    
    # 4. Remover constraint única nova
    op.drop_constraint("uq_profile_tenant_membership_hospital", "profile", type_="unique")
    
    # 5. Remover foreign key e índice de membership_id
    op.drop_index(op.f("ix_profile_membership_id"), table_name="profile")
    op.drop_constraint("profile_membership_id_fkey", "profile", type_="foreignkey")
    
    # 6. Remover coluna membership_id
    op.drop_column("profile", "membership_id")
    
    # 7. Tornar account_id NOT NULL
    op.alter_column(
        "profile",
        "account_id",
        existing_type=sa.Integer(),
        nullable=False
    )
    
    # 8. Criar foreign key para account.id
    op.create_foreign_key(
        "profile_account_id_fkey",
        "profile",
        "account",
        ["account_id"],
        ["id"]
    )
    
    # 9. Criar índice em account_id
    op.create_index(
        op.f("ix_profile_account_id"),
        "profile",
        ["account_id"],
        unique=False
    )
    
    # 10. Recriar constraint única antiga
    op.execute("""
        CREATE UNIQUE INDEX uq_profile_tenant_account_no_hospital
        ON profile (tenant_id, account_id)
        WHERE hospital_id IS NULL
    """)
    
    # 11. Recriar constraint única antiga
    op.create_unique_constraint(
        "uq_profile_tenant_account_hospital",
        "profile",
        ["tenant_id", "account_id", "hospital_id"]
    )
