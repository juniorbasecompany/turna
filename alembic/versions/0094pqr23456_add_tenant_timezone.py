"""add tenant timezone (IANA)

Revision ID: 0094pqr23456
Revises: 0093mno12345
Create Date: 2026-01-14 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0094pqr23456"
down_revision: Union[str, None] = "0093mno12345"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenant",
        sa.Column("timezone", sa.String(), nullable=False, server_default="UTC"),
    )


def downgrade() -> None:
    op.drop_column("tenant", "timezone")

