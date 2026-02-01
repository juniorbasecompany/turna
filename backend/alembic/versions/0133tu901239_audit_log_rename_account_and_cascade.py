"""audit_log: rename actor_account_id to account_id, FK ON DELETE CASCADE

Revision ID: 0133tu901239
Revises: 0132rs901238
Create Date: 2026-02-01 15:00:00.000000

- Renomeia coluna actor_account_id para account_id
- Define tenant_id, account_id e member_id como ON DELETE CASCADE
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0133tu901239"
down_revision: Union[str, None] = "0132rs901238"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Remover FKs existentes
    op.drop_constraint("audit_log_tenant_id_fkey", "audit_log", type_="foreignkey")
    op.drop_constraint("audit_log_actor_account_id_fkey", "audit_log", type_="foreignkey")
    op.drop_constraint("audit_log_member_id_fkey", "audit_log", type_="foreignkey")

    # 2. Renomear coluna e índice actor_account_id -> account_id
    op.drop_index(op.f("ix_audit_log_actor_account_id"), table_name="audit_log")
    op.alter_column(
        "audit_log",
        "actor_account_id",
        new_column_name="account_id",
    )
    op.create_index(op.f("ix_audit_log_account_id"), "audit_log", ["account_id"], unique=False)

    # 3. Recriar FKs com ON DELETE CASCADE
    op.create_foreign_key(
        "audit_log_tenant_id_fkey",
        "audit_log",
        "tenant",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "audit_log_account_id_fkey",
        "audit_log",
        "account",
        ["account_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "audit_log_member_id_fkey",
        "audit_log",
        "member",
        ["member_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # 1. Remover FKs com CASCADE
    op.drop_constraint("audit_log_tenant_id_fkey", "audit_log", type_="foreignkey")
    op.drop_constraint("audit_log_account_id_fkey", "audit_log", type_="foreignkey")
    op.drop_constraint("audit_log_member_id_fkey", "audit_log", type_="foreignkey")

    # 2. Renomear coluna e índice account_id -> actor_account_id
    op.drop_index(op.f("ix_audit_log_account_id"), table_name="audit_log")
    op.alter_column(
        "audit_log",
        "account_id",
        new_column_name="actor_account_id",
    )
    op.create_index(
        op.f("ix_audit_log_actor_account_id"),
        "audit_log",
        ["actor_account_id"],
        unique=False,
    )

    # 3. Recriar FKs sem ON DELETE CASCADE (comportamento padrão)
    op.create_foreign_key(
        "audit_log_tenant_id_fkey",
        "audit_log",
        "tenant",
        ["tenant_id"],
        ["id"],
    )
    op.create_foreign_key(
        "audit_log_actor_account_id_fkey",
        "audit_log",
        "account",
        ["actor_account_id"],
        ["id"],
    )
    op.create_foreign_key(
        "audit_log_member_id_fkey",
        "audit_log",
        "member",
        ["member_id"],
        ["id"],
    )
