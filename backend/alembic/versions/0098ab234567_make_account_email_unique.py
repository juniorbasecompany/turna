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


def _scalar_or_default(conn, sql: str, default):
    if getattr(op.get_context(), "as_sql", False):
        return default

    result = conn.execute(sa.text(sql))
    return result.scalar()


def upgrade() -> None:
    conn = op.get_bind()

    # Remove constraint antiga (email, tenant_id) se existir.
    old_constraint_exists = _scalar_or_default(
        conn,
        """
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'account'
          AND constraint_type = 'UNIQUE'
          AND constraint_name = 'uq_account_email_tenant'
        """,
        "uq_account_email_tenant",
    )
    if old_constraint_exists:
        op.drop_constraint("uq_account_email_tenant", "account", type_="unique")

    # Cria constraint global (email) se ainda não existir.
    new_constraint_exists = _scalar_or_default(
        conn,
        """
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'account'
          AND constraint_type = 'UNIQUE'
          AND constraint_name = 'uq_account_email'
        """,
        None,
    )
    if not new_constraint_exists:
        op.create_unique_constraint("uq_account_email", "account", ["email"])


def downgrade() -> None:
    conn = op.get_bind()

    global_constraint_exists = _scalar_or_default(
        conn,
        """
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'account'
          AND constraint_type = 'UNIQUE'
          AND constraint_name = 'uq_account_email'
        """,
        "uq_account_email",
    )
    if global_constraint_exists:
        op.drop_constraint("uq_account_email", "account", type_="unique")

    tenant_constraint_exists = _scalar_or_default(
        conn,
        """
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'account'
          AND constraint_type = 'UNIQUE'
          AND constraint_name = 'uq_account_email_tenant'
        """,
        None,
    )
    if not tenant_constraint_exists:
        op.create_unique_constraint("uq_account_email_tenant", "account", ["email", "tenant_id"])

