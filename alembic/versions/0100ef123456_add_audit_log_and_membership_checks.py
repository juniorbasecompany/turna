"""add audit_log table and harden membership enums

Revision ID: 0100ef123456
Revises: 0099cd345678
Create Date: 2026-01-16 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0100ef123456"
down_revision: Union[str, None] = "0099cd345678"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _constraint_exists(conn, *, table_name: str, constraint_name: str) -> bool:
    found = conn.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.table_constraints
            WHERE table_name = :table_name
              AND constraint_name = :constraint_name
            """
        ),
        {"table_name": table_name, "constraint_name": constraint_name},
    ).scalar()
    return bool(found)


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=True),
        sa.Column("actor_account_id", sa.Integer(), nullable=False),
        sa.Column("membership_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.ForeignKeyConstraint(["actor_account_id"], ["account.id"]),
        sa.ForeignKeyConstraint(["membership_id"], ["membership.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_log_tenant_id"), "audit_log", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_audit_log_actor_account_id"), "audit_log", ["actor_account_id"], unique=False)
    op.create_index(op.f("ix_audit_log_membership_id"), "audit_log", ["membership_id"], unique=False)
    op.create_index(op.f("ix_audit_log_event_type"), "audit_log", ["event_type"], unique=False)

    conn = op.get_bind()

    # Hardening: garante que role/status não saem do enum (tabela legacy usa String).
    ck_role = "ck_membership_role_valid"
    if not _constraint_exists(conn, table_name="membership", constraint_name=ck_role):
        op.create_check_constraint(
            ck_role,
            "membership",
            "role IN ('admin','user')",
        )

    ck_status = "ck_membership_status_valid"
    if not _constraint_exists(conn, table_name="membership", constraint_name=ck_status):
        op.create_check_constraint(
            ck_status,
            "membership",
            "status IN ('PENDING','ACTIVE','REJECTED','REMOVED')",
        )


def downgrade() -> None:
    conn = op.get_bind()

    ck_status = "ck_membership_status_valid"
    if _constraint_exists(conn, table_name="membership", constraint_name=ck_status):
        op.drop_constraint(ck_status, "membership", type_="check")

    ck_role = "ck_membership_role_valid"
    if _constraint_exists(conn, table_name="membership", constraint_name=ck_role):
        op.drop_constraint(ck_role, "membership", type_="check")

    op.drop_index(op.f("ix_audit_log_event_type"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_membership_id"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_actor_account_id"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_tenant_id"), table_name="audit_log")
    op.drop_table("audit_log")

