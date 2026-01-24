"""add professional table

Revision ID: 0110yz012345
Revises: 0109wx012345
Create Date: 2026-01-18 11:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0110yz012345"
down_revision: Union[str, None] = "0109wx012345"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Criar tabela professional
    op.create_table(
        "professional",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
    )

    # Criar índices
    op.create_index(op.f("ix_professional_tenant_id"), "professional", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_professional_name"), "professional", ["name"], unique=False)
    op.create_index(op.f("ix_professional_email"), "professional", ["email"], unique=False)
    op.create_index(op.f("ix_professional_active"), "professional", ["active"], unique=False)

    # Constraint única: nome único por tenant
    op.create_unique_constraint(
        "uq_professional_tenant_name",
        "professional",
        ["tenant_id", "name"],
    )


def downgrade() -> None:
    # Remover constraint única
    op.drop_constraint("uq_professional_tenant_name", "professional", type_="unique")

    # Remover índices
    op.drop_index(op.f("ix_professional_active"), table_name="professional")
    op.drop_index(op.f("ix_professional_email"), table_name="professional")
    op.drop_index(op.f("ix_professional_name"), table_name="professional")
    op.drop_index(op.f("ix_professional_tenant_id"), table_name="professional")

    # Remover tabela
    op.drop_table("professional")
