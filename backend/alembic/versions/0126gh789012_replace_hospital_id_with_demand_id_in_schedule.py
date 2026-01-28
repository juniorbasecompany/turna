"""replace hospital_id with demand_id in schedule

Revision ID: 0126gh789012
Revises: 0125ef678901
Create Date: 2026-01-28 10:00:00.000000

Cada Demand gera exatamente uma Schedule (relação 1:1).
- Remove hospital_id (hospital é obtido via demand.hospital_id)
- Adiciona demand_id NOT NULL UNIQUE com ON DELETE CASCADE
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0126gh789012"
down_revision: Union[str, None] = "0125ef678901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Substitui hospital_id por demand_id em schedule:
    - Remove FK e coluna hospital_id
    - Adiciona coluna demand_id NOT NULL UNIQUE com FK ON DELETE CASCADE
    
    Nota: tabela schedule deve estar vazia para esta migração.
    """
    # 1. Remover FK hospital_id
    op.drop_constraint("fk_schedule_hospital_id", "schedule", type_="foreignkey")
    
    # 2. Remover índice de hospital_id
    op.drop_index(op.f("ix_schedule_hospital_id"), table_name="schedule")
    
    # 3. Remover coluna hospital_id
    op.drop_column("schedule", "hospital_id")
    
    # 4. Adicionar coluna demand_id NOT NULL
    op.add_column(
        "schedule",
        sa.Column("demand_id", sa.Integer(), nullable=False),
    )
    
    # 5. Criar índice único em demand_id (garante relação 1:1)
    op.create_index(
        op.f("ix_schedule_demand_id"),
        "schedule",
        ["demand_id"],
        unique=True,
    )
    
    # 6. Criar FK com ON DELETE CASCADE
    op.create_foreign_key(
        "fk_schedule_demand_id",
        "schedule",
        "demand",
        ["demand_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """
    Reverte para hospital_id (sem demand_id).
    
    Nota: tabela schedule deve estar vazia para esta migração.
    """
    # 1. Remover FK demand_id
    op.drop_constraint("fk_schedule_demand_id", "schedule", type_="foreignkey")
    
    # 2. Remover índice único de demand_id
    op.drop_index(op.f("ix_schedule_demand_id"), table_name="schedule")
    
    # 3. Remover coluna demand_id
    op.drop_column("schedule", "demand_id")
    
    # 4. Adicionar coluna hospital_id NOT NULL
    op.add_column(
        "schedule",
        sa.Column("hospital_id", sa.Integer(), nullable=False),
    )
    
    # 5. Criar índice em hospital_id
    op.create_index(
        op.f("ix_schedule_hospital_id"),
        "schedule",
        ["hospital_id"],
        unique=False,
    )
    
    # 6. Criar FK com ON DELETE RESTRICT
    op.create_foreign_key(
        "fk_schedule_hospital_id",
        "schedule",
        "hospital",
        ["hospital_id"],
        ["id"],
        ondelete="RESTRICT",
    )
