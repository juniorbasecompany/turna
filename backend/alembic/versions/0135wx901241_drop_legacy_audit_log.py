"""drop legacy audit_log table

Revision ID: 0135wx901241
Revises: 0134uv901240
Create Date: 2026-03-15 21:30:00.000000

- Remove audit_log de bancos existentes
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0135wx901241"
down_revision: Union[str, None] = "0134uv901240"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove a tabela legada apenas quando ela existir.
    op.execute(sa.text("DROP TABLE IF EXISTS audit_log"))


def downgrade() -> None:
    # A tabela foi removida do histórico do projeto.
    pass
