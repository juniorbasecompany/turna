"""ensure membership email is filled for existing memberships

Revision ID: 0115ij012345
Revises: 0114gh012345
Create Date: 2026-01-21 08:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0115ij012345"
down_revision: Union[str, None] = "0114gh012345"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Garantir que todos os memberships existentes tenham email preenchido.
    Preenche membership.email a partir de account.email para memberships que têm account_id mas email NULL.
    """
    conn = op.get_bind()
    
    # Preencher email dos memberships existentes que têm account_id mas email NULL
    conn.execute(sa.text("""
        UPDATE membership
        SET email = account.email
        FROM account
        WHERE membership.account_id = account.id
          AND membership.email IS NULL
          AND account.email IS NOT NULL
    """))


def downgrade() -> None:
    # Esta migração apenas preenche dados, não altera schema
    # Não há necessidade de reverter
    pass
