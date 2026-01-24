"""add job.started_at (timestamptz)

Revision ID: 0095stu34567
Revises: 0094pqr23456
Create Date: 2026-01-15 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0095stu34567"
down_revision: Union[str, None] = "0094pqr23456"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "job",
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("job", "started_at")

