"""Make tenant slug optional

Revision ID: 0134vw901240
Revises: 0133tu901239
Create Date: 2026-02-01 16:00:00.000000

- Torna slug do tenant opcional (nullable)
- Unique constraint permite múltiplos NULL
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0134vw901240"
down_revision: Union[str, None] = "0133tu901239"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "tenant",
        "slug",
        existing_type=sa.String(),
        nullable=True,
    )


def downgrade() -> None:
    op.execute(sa.text("UPDATE tenant SET slug = 'tenant-' || id::text WHERE slug IS NULL"))
    op.alter_column(
        "tenant",
        "slug",
        existing_type=sa.String(),
        nullable=False,
    )
