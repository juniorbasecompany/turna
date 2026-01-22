"""remove professional table

Revision ID: 0118op012345
Revises: 0117mn012345
Create Date: 2026-01-21 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0118op012345"
down_revision: Union[str, None] = "0117mn012345"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove a tabela professional completamente.
    
    Passos:
    1. Remover constraint única uq_professional_tenant_name
    2. Remover índices
    3. Remover foreign keys
    4. Dropar a tabela professional
    """
    # 1. Remover constraint única
    op.drop_constraint("uq_professional_tenant_name", "professional", type_="unique")
    
    # 2. Remover índices
    op.drop_index(op.f("ix_professional_tenant_id"), table_name="professional")
    op.drop_index(op.f("ix_professional_name"), table_name="professional")
    op.drop_index(op.f("ix_professional_email"), table_name="professional")
    op.drop_index(op.f("ix_professional_active"), table_name="professional")
    op.drop_index(op.f("ix_professional_membership_id"), table_name="professional")
    
    # 3. Remover foreign keys
    op.drop_constraint("professional_membership_id_fkey", "professional", type_="foreignkey")
    # Verificar se existe foreign key para tenant (pode não ter nome explícito)
    # Se houver, será removida automaticamente ao dropar a tabela
    
    # 4. Dropar a tabela
    op.drop_table("professional")


def downgrade() -> None:
    """
    Reverter: recriar tabela professional.
    Nota: Esta operação não restaura dados, apenas a estrutura da tabela.
    """
    # Recriar tabela professional (estrutura básica)
    op.create_table(
        "professional",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("membership_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.ForeignKeyConstraint(["membership_id"], ["membership.id"]),
    )
    
    # Recriar índices
    op.create_index(op.f("ix_professional_tenant_id"), "professional", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_professional_name"), "professional", ["name"], unique=False)
    op.create_index(op.f("ix_professional_email"), "professional", ["email"], unique=False)
    op.create_index(op.f("ix_professional_active"), "professional", ["active"], unique=False)
    op.create_index(op.f("ix_professional_membership_id"), "professional", ["membership_id"], unique=False)
    
    # Recriar constraint única
    op.create_unique_constraint(
        "uq_professional_tenant_name",
        "professional",
        ["tenant_id", "name"],
    )
