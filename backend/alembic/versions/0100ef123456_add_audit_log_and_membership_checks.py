"""harden membership enums

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
    if getattr(op.get_context(), "as_sql", False):
        return False

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
    if getattr(op.get_context(), "as_sql", False) or _constraint_exists(conn, table_name="membership", constraint_name=ck_status):
        op.drop_constraint(ck_status, "membership", type_="check")

    ck_role = "ck_membership_role_valid"
    if getattr(op.get_context(), "as_sql", False) or _constraint_exists(conn, table_name="membership", constraint_name=ck_role):
        op.drop_constraint(ck_role, "membership", type_="check")

