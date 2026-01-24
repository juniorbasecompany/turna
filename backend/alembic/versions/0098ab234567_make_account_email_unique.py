"""make account.email globally unique

Revision ID: 0098ab234567
Revises: 0097yz012345
Create Date: 2026-01-16 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0098ab234567"
down_revision: Union[str, None] = "0097yz012345"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Remove constraint antiga (email, tenant_id) se existir.
    result = conn.execute(
        sa.text(
            """
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'account'
              AND constraint_type = 'UNIQUE'
              AND constraint_name = 'uq_account_email_tenant'
            """
        )
    )
    if result.scalar():
        op.drop_constraint("uq_account_email_tenant", "account", type_="unique")

    # Cria constraint global (email) se ainda não existir.
    result = conn.execute(
        sa.text(
            """
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'account'
              AND constraint_type = 'UNIQUE'
              AND constraint_name = 'uq_account_email'
            """
        )
    )
    if not result.scalar():
        op.create_unique_constraint("uq_account_email", "account", ["email"])


def downgrade() -> None:
    conn = op.get_bind()

    result = conn.execute(
        sa.text(
            """
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'account'
              AND constraint_type = 'UNIQUE'
              AND constraint_name = 'uq_account_email'
            """
        )
    )
    if result.scalar():
        op.drop_constraint("uq_account_email", "account", type_="unique")

    result = conn.execute(
        sa.text(
            """
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = 'account'
              AND constraint_type = 'UNIQUE'
              AND constraint_name = 'uq_account_email_tenant'
            """
        )
    )
    if not result.scalar():
        op.create_unique_constraint("uq_account_email_tenant", "account", ["email", "tenant_id"])

