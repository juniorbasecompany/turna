"""migrate role user->account and update constraints

Revision ID: 0101gh234567
Revises: 0100ef123456
Create Date: 2026-01-16 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0101gh234567"
down_revision: Union[str, None] = "0100ef123456"
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
    conn = op.get_bind()

    # 1) Dropa check antigo (permitia apenas admin/user), senão o UPDATE falha.
    ck_role = "ck_membership_role_valid"
    if _constraint_exists(conn, table_name="membership", constraint_name=ck_role):
        op.drop_constraint(ck_role, "membership", type_="check")

    # 2) Migra dados históricos: membership.role e account.role.
    op.execute(sa.text("UPDATE membership SET role = 'account' WHERE role = 'user'"))
    op.execute(sa.text("UPDATE account SET role = 'account' WHERE role = 'user'"))

    # 3) Atualiza defaults no banco para novos registros.
    op.alter_column("membership", "role", existing_type=sa.String(), server_default="account")
    op.alter_column("account", "role", existing_type=sa.String(), server_default="account")

    # 4) Atualiza audit_log.data (JSON) quando contém role serializada.
    # Observação: usamos jsonb_set em data::jsonb e voltamos para json.
    op.execute(
        sa.text(
            """
            UPDATE audit_log
            SET data = jsonb_set(data::jsonb, '{to_role}', '"account"', true)::json
            WHERE data IS NOT NULL
              AND (data::jsonb ? 'to_role')
              AND (data::jsonb ->> 'to_role') = 'user'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE audit_log
            SET data = jsonb_set(data::jsonb, '{from_role}', '"account"', true)::json
            WHERE data IS NOT NULL
              AND (data::jsonb ? 'from_role')
              AND (data::jsonb ->> 'from_role') = 'user'
            """
        )
    )

    # 5) Recria check constraint alinhado com o novo valor.
    op.create_check_constraint(
        ck_role,
        "membership",
        "role IN ('admin','account')",
    )


def downgrade() -> None:
    conn = op.get_bind()

    ck_role = "ck_membership_role_valid"
    if _constraint_exists(conn, table_name="membership", constraint_name=ck_role):
        op.drop_constraint(ck_role, "membership", type_="check")

    op.execute(sa.text("UPDATE membership SET role = 'user' WHERE role = 'account'"))
    op.execute(sa.text("UPDATE account SET role = 'user' WHERE role = 'account'"))

    op.alter_column("membership", "role", existing_type=sa.String(), server_default="user")
    op.alter_column("account", "role", existing_type=sa.String(), server_default="user")

    op.execute(
        sa.text(
            """
            UPDATE audit_log
            SET data = jsonb_set(data::jsonb, '{to_role}', '"user"', true)::json
            WHERE data IS NOT NULL
              AND (data::jsonb ? 'to_role')
              AND (data::jsonb ->> 'to_role') = 'account'
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE audit_log
            SET data = jsonb_set(data::jsonb, '{from_role}', '"user"', true)::json
            WHERE data IS NOT NULL
              AND (data::jsonb ? 'from_role')
              AND (data::jsonb ->> 'from_role') = 'account'
            """
        )
    )

    op.create_check_constraint(
        ck_role,
        "membership",
        "role IN ('admin','user')",
    )

