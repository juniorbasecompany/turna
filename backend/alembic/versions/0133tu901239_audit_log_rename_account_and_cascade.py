"""legacy no-op after audit_log removal

Revision ID: 0133tu901239
Revises: 0132rs901238
Create Date: 2026-02-01 15:00:00.000000

- Revisão preservada apenas para manter a cadeia do Alembic estável
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0133tu901239"
down_revision: Union[str, None] = "0132rs901238"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
