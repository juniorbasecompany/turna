"""add membership table (account<->tenant) and backfill

Revision ID: 0097yz012345
Revises: 0096vwx45678
Create Date: 2026-01-16 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0097yz012345"
down_revision: Union[str, None] = "0096vwx45678"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "membership",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="user"),
        sa.Column("status", sa.String(), nullable=False, server_default="ACTIVE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.ForeignKeyConstraint(["account_id"], ["account.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "account_id", name="uq_membership_tenant_account"),
    )
    op.create_index(op.f("ix_membership_tenant_id"), "membership", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_membership_account_id"), "membership", ["account_id"], unique=False)
    op.create_index(op.f("ix_membership_role"), "membership", ["role"], unique=False)
    op.create_index(op.f("ix_membership_status"), "membership", ["status"], unique=False)

    # Backfill: todo account existente vira ACTIVE no tenant atual.
    # Usa ON CONFLICT (uq_membership_tenant_account) para não duplicar.
    op.execute(
        sa.text(
            """
            INSERT INTO membership (tenant_id, account_id, role, status, created_at, updated_at)
            SELECT a.tenant_id, a.id, a.role, 'ACTIVE', a.created_at, a.updated_at
            FROM account a
            WHERE a.tenant_id IS NOT NULL
            ON CONFLICT (tenant_id, account_id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_membership_status"), table_name="membership")
    op.drop_index(op.f("ix_membership_role"), table_name="membership")
    op.drop_index(op.f("ix_membership_account_id"), table_name="membership")
    op.drop_index(op.f("ix_membership_tenant_id"), table_name="membership")
    op.drop_table("membership")

