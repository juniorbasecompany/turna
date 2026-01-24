"""add hospital table and hospital_id to file

Revision ID: 0105op678901
Revises: 0104mn567890
Create Date: 2026-01-17 02:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0105op678901"
down_revision: Union[str, None] = "0104mn567890"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Criar tabela hospital
    op.create_table(
        "hospital",
        sa.Column("id", sa.Integer(), nullable=False, primary_key=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("prompt", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.UniqueConstraint("tenant_id", "name", name="uq_hospital_tenant_name"),
    )

    # Criar índice em tenant_id
    op.create_index(op.f("ix_hospital_tenant_id"), "hospital", ["tenant_id"], unique=False)

    # Como as tabelas estão vazias, podemos adicionar hospital_id diretamente como NOT NULL
    # Primeiro criar a coluna como nullable temporariamente (para permitir criação da FK)
    op.add_column(
        "file",
        sa.Column("hospital_id", sa.Integer(), nullable=True),
    )

    # Criar FK
    op.create_foreign_key(
        "fk_file_hospital_id",
        "file",
        "hospital",
        ["hospital_id"],
        ["id"],
    )

    # Como as tabelas estão vazias, podemos tornar NOT NULL diretamente
    # Mas primeiro precisamos criar pelo menos um hospital para cada tenant existente
    # Como as tabelas estão vazias, não há problema em tornar NOT NULL diretamente
    op.alter_column("file", "hospital_id", nullable=False)

    # Criar índice composto (tenant_id, hospital_id)
    op.create_index(
        "ix_file_tenant_id_hospital_id",
        "file",
        ["tenant_id", "hospital_id"],
        unique=False,
    )


def downgrade() -> None:
    # Remover índice composto
    op.drop_index("ix_file_tenant_id_hospital_id", table_name="file")

    # Remover FK e coluna hospital_id
    op.drop_constraint("fk_file_hospital_id", "file", type_="foreignkey")
    op.drop_column("file", "hospital_id")

    # Remover tabela hospital
    op.drop_index(op.f("ix_hospital_tenant_id"), table_name="hospital")
    op.drop_table("hospital")
