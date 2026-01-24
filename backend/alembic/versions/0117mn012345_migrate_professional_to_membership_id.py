"""migrate professional account_id to membership_id

Revision ID: 0117mn012345
Revises: 0116kl012345
Create Date: 2026-01-21 09:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0117mn012345"
down_revision: Union[str, None] = "0116kl012345"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Migra Professional de account_id para membership_id.
    
    Passos:
    1. Adicionar coluna membership_id (nullable, pois professional pode não ter account)
    2. Preencher membership_id a partir de account_id (via Membership) quando account_id não é NULL
    3. Remover foreign key e índice de account_id
    4. Remover coluna account_id
    5. Criar foreign key para membership.id (nullable)
    6. Criar índice em membership_id
    """
    conn = op.get_bind()
    
    # 1. Adicionar coluna membership_id (nullable, pois professional pode não ter account)
    op.add_column(
        "professional",
        sa.Column("membership_id", sa.Integer(), nullable=True)
    )
    
    # 2. Preencher membership_id a partir de account_id (via Membership)
    # Para cada professional com account_id, encontrar o membership ACTIVE correspondente
    conn.execute(sa.text("""
        UPDATE professional
        SET membership_id = membership.id
        FROM membership
        WHERE professional.account_id = membership.account_id
          AND professional.tenant_id = membership.tenant_id
          AND membership.status = 'ACTIVE'
    """))
    
    # 3. Remover foreign key e índice de account_id
    op.drop_index(op.f("ix_professional_account_id"), table_name="professional")
    op.drop_constraint("fk_professional_account_id", "professional", type_="foreignkey")
    
    # 4. Remover coluna account_id
    op.drop_column("professional", "account_id")
    
    # 5. Criar foreign key para membership.id (nullable)
    op.create_foreign_key(
        "professional_membership_id_fkey",
        "professional",
        "membership",
        ["membership_id"],
        ["id"]
    )
    
    # 6. Criar índice em membership_id
    op.create_index(
        op.f("ix_professional_membership_id"),
        "professional",
        ["membership_id"],
        unique=False
    )


def downgrade() -> None:
    """
    Reverter migração: membership_id -> account_id
    """
    conn = op.get_bind()
    
    # 1. Adicionar coluna account_id (nullable)
    op.add_column(
        "professional",
        sa.Column("account_id", sa.Integer(), nullable=True)
    )
    
    # 2. Preencher account_id a partir de membership_id (via Membership)
    conn.execute(sa.text("""
        UPDATE professional
        SET account_id = membership.account_id
        FROM membership
        WHERE professional.membership_id = membership.id
    """))
    
    # 3. Remover foreign key e índice de membership_id
    op.drop_index(op.f("ix_professional_membership_id"), table_name="professional")
    op.drop_constraint("professional_membership_id_fkey", "professional", type_="foreignkey")
    
    # 4. Remover coluna membership_id
    op.drop_column("professional", "membership_id")
    
    # 5. Criar foreign key para account.id (nullable)
    op.create_foreign_key(
        "fk_professional_account_id",
        "professional",
        "account",
        ["account_id"],
        ["id"]
    )
    
    # 6. Criar índice em account_id
    op.create_index(
        op.f("ix_professional_account_id"),
        "professional",
        ["account_id"],
        unique=False
    )
