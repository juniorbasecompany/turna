from __future__ import annotations

import enum

import sqlalchemy as sa
from sqlmodel import Field

from app.model.base import BaseModel


class MembershipRole(str, enum.Enum):
    ADMIN = "admin"
    ACCOUNT = "account"


class MembershipStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"
    REMOVED = "REMOVED"


class Membership(BaseModel, table=True):
    """
    Vínculo Account ↔ Tenant (multi-tenant correto).

    Observações:
      - `role` e `status` vivem no Membership (não no Account).
      - Um Account pode ter múltiplos memberships (um por tenant).
    """

    __tablename__ = "membership"

    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    account_id: int = Field(foreign_key="account.id", index=True)

    # Importante: persistir enums pelos *values* ("admin"/"account", etc),
    # pois o banco usa strings.
    role: MembershipRole = Field(
        default=MembershipRole.ACCOUNT,
        sa_type=sa.Enum(
            MembershipRole,
            name="membership_role",
            native_enum=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        index=True,
    )
    status: MembershipStatus = Field(
        default=MembershipStatus.ACTIVE,
        sa_type=sa.Enum(
            MembershipStatus,
            name="membership_status",
            native_enum=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        index=True,
    )

