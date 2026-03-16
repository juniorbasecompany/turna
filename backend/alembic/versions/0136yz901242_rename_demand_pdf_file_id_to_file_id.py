"""rename demand pdf_file_id to file_id

Revision ID: 0136yz901242
Revises: 0135wx901241
Create Date: 2026-03-16 00:10:00.000000

Renomeia o vínculo do arquivo de origem em demand para refletir a semântica correta.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0136yz901242"
down_revision: Union[str, None] = "0135wx901241"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("fk_demand_pdf_file_id", "demand", type_="foreignkey")
    op.drop_index(op.f("ix_demand_pdf_file_id"), table_name="demand")
    op.alter_column("demand", "pdf_file_id", new_column_name="file_id")
    op.create_index(op.f("ix_demand_file_id"), "demand", ["file_id"], unique=False)
    op.create_foreign_key(
        "fk_demand_file_id",
        "demand",
        "file",
        ["file_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_demand_file_id", "demand", type_="foreignkey")
    op.drop_index(op.f("ix_demand_file_id"), table_name="demand")
    op.alter_column("demand", "file_id", new_column_name="pdf_file_id")
    op.create_index(op.f("ix_demand_pdf_file_id"), "demand", ["pdf_file_id"], unique=False)
    op.create_foreign_key(
        "fk_demand_pdf_file_id",
        "demand",
        "file",
        ["pdf_file_id"],
        ["id"],
        ondelete="SET NULL",
    )
