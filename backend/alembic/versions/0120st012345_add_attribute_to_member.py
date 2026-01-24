"""add attribute to member

Revision ID: 0120st012345
Revises: 0119qr012345
Create Date: 2026-01-22 04:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0120st012345"
down_revision: Union[str, None] = "0119qr012345"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Adiciona campo attribute (JSON) na tabela member.
    """
    op.add_column(
        "member",
        sa.Column(
            "attribute",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
    )


def downgrade() -> None:
    """
    Remove campo attribute da tabela member.
    """
    op.drop_column("member", "attribute")
