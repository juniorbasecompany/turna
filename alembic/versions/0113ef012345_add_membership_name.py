"""add membership name field

Revision ID: 0113ef012345
Revises: 0112cd012345
Create Date: 2026-01-21 06:57:02.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0113ef012345"
down_revision: Union[str, None] = "0112cd012345"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Adicionar campo name em membership (nullable)
    op.add_column(
        "membership",
        sa.Column("name", sa.String(), nullable=True)
    )

    # Backfill: copiar account.name → membership.name para memberships ACTIVE
    # Usando raw SQL para fazer o JOIN e UPDATE
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE membership
        SET name = account.name
        FROM account
        WHERE membership.account_id = account.id
          AND membership.status = 'ACTIVE'
          AND account.name IS NOT NULL
          AND account.name != ''
    """))


def downgrade() -> None:
    # Remover campo name
    op.drop_column("membership", "name")
