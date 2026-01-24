"""remove tenant_id from account

Revision ID: 0099cd345678
Revises: 0098ab234567
Create Date: 2026-01-16 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0099cd345678"
down_revision: Union[str, None] = "0098ab234567"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Safety: nenhum account pode ficar órfão (sem memberships).
    orphan_count = conn.execute(
        sa.text(
            """
            SELECT COUNT(*)
            FROM account a
            WHERE NOT EXISTS (
                SELECT 1 FROM membership m WHERE m.account_id = a.id
            )
            """
        )
    ).scalar()
    if int(orphan_count or 0) > 0:
        raise RuntimeError(f"Abort: existem {orphan_count} account(s) sem membership")

    # Drop FK se existir.
    fk_exists = conn.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.table_constraints
            WHERE table_name = 'account'
              AND constraint_type = 'FOREIGN KEY'
              AND constraint_name = 'account_tenant_id_fkey'
            """
        )
    ).scalar()
    if fk_exists:
        op.drop_constraint("account_tenant_id_fkey", "account", type_="foreignkey")

    # Drop index se existir.
    ix_exists = conn.execute(
        sa.text(
            """
            SELECT 1
            FROM pg_indexes
            WHERE tablename = 'account'
              AND indexname = 'ix_account_tenant_id'
            """
        )
    ).scalar()
    if ix_exists:
        op.drop_index("ix_account_tenant_id", table_name="account")

    # Drop column (se existir).
    col_exists = conn.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'account'
              AND column_name = 'tenant_id'
            """
        )
    ).scalar()
    if col_exists:
        op.drop_column("account", "tenant_id")


def downgrade() -> None:
    conn = op.get_bind()

    col_exists = conn.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'account'
              AND column_name = 'tenant_id'
            """
        )
    ).scalar()
    if not col_exists:
        op.add_column("account", sa.Column("tenant_id", sa.Integer(), nullable=True))

    fk_exists = conn.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.table_constraints
            WHERE table_name = 'account'
              AND constraint_type = 'FOREIGN KEY'
              AND constraint_name = 'account_tenant_id_fkey'
            """
        )
    ).scalar()
    if not fk_exists:
        op.create_foreign_key("account_tenant_id_fkey", "account", "tenant", ["tenant_id"], ["id"])

    ix_exists = conn.execute(
        sa.text(
            """
            SELECT 1
            FROM pg_indexes
            WHERE tablename = 'account'
              AND indexname = 'ix_account_tenant_id'
            """
        )
    ).scalar()
    if not ix_exists:
        op.create_index("ix_account_tenant_id", "account", ["tenant_id"], unique=False)

    # Best-effort backfill usando um tenant ACTIVE qualquer (menor tenant_id).
    conn.execute(
        sa.text(
            """
            UPDATE account a
            SET tenant_id = sub.tenant_id
            FROM (
                SELECT account_id, MIN(tenant_id) AS tenant_id
                FROM membership
                WHERE status = 'ACTIVE'
                GROUP BY account_id
            ) sub
            WHERE a.id = sub.account_id
              AND a.tenant_id IS NULL
            """
        )
    )
