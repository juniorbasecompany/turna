"""tenant: slug->label (optional); member, hospital: add label (optional, unique per tenant)

Revision ID: 0134uv901240
Revises: 0133tu901239
Create Date: 2026-02-01 16:00:00.000000

- Tenant: rename slug to label, make nullable, unique only when not null
- Member: add label (nullable), unique (tenant_id, label) when label not null
- Hospital: add label (nullable), unique (tenant_id, label) when label not null
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0134uv901240"
down_revision: Union[str, None] = "0134vw901240"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Tenant: slug -> label, unique when not null (slug já nullable por 0134vw901240)
    op.drop_index("ix_tenant_slug", table_name="tenant")
    op.alter_column(
        "tenant",
        "slug",
        new_column_name="label",
        nullable=True,
    )
    # Partial unique: only when label is not null
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX uq_tenant_label ON tenant (label) WHERE label IS NOT NULL"
        )
    )
    op.create_index("ix_tenant_label", "tenant", ["label"], unique=False)

    # 2. Member: add label column
    op.add_column(
        "member",
        sa.Column("label", sa.String(), nullable=True),
    )
    op.create_index("ix_member_label", "member", ["label"], unique=False)
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX uq_member_tenant_label "
            "ON member (tenant_id, label) WHERE label IS NOT NULL"
        )
    )

    # 3. Hospital: add label column
    op.add_column(
        "hospital",
        sa.Column("label", sa.String(), nullable=True),
    )
    op.create_index("ix_hospital_label", "hospital", ["label"], unique=False)
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX uq_hospital_tenant_label "
            "ON hospital (tenant_id, label) WHERE label IS NOT NULL"
        )
    )


def downgrade() -> None:
    # 3. Hospital: remove label
    op.execute(sa.text("DROP INDEX IF EXISTS uq_hospital_tenant_label"))
    op.drop_index("ix_hospital_label", table_name="hospital")
    op.drop_column("hospital", "label")

    # 2. Member: remove label
    op.execute(sa.text("DROP INDEX IF EXISTS uq_member_tenant_label"))
    op.drop_index("ix_member_label", table_name="member")
    op.drop_column("member", "label")

    # 1. Tenant: label -> slug (0134vw deixa slug nullable)
    op.execute(sa.text("DROP INDEX IF EXISTS uq_tenant_label"))
    op.drop_index("ix_tenant_label", table_name="tenant", if_exists=True)
    op.alter_column(
        "tenant",
        "label",
        new_column_name="slug",
    )
    op.create_index("ix_tenant_slug", "tenant", ["slug"], unique=True)
