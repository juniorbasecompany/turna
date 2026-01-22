from __future__ import annotations

import enum

import sqlalchemy as sa
from sqlmodel import Field, Column
from sqlalchemy import JSON

from app.model.base import BaseModel


class MemberRole(str, enum.Enum):
    ADMIN = "admin"
    ACCOUNT = "account"


class MemberStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    REJECTED = "REJECTED"
    REMOVED = "REMOVED"


class Member(BaseModel, table=True):
    """
    Vínculo Account ↔ Tenant (multi-tenant correto).

    Observações:
      - `role` e `status` vivem no Member (não no Account).
      - Um Account pode ter múltiplos members (um por tenant).
      - `account_id` pode ser NULL para convites pendentes (antes do usuário aceitar).
      - Quando `account_id` é NULL, `email` identifica o convite pendente.
    """

    __tablename__ = "member"

    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    account_id: int | None = Field(foreign_key="account.id", index=True, nullable=True, default=None)

    # Email para identificar convites pendentes (quando account_id é NULL)
    # Após aceitar, o email pode ser obtido via account.email
    email: str | None = Field(default=None, nullable=True, index=True)

    # Importante: persistir enums pelos *values* ("admin"/"account", etc),
    # pois o banco usa strings.
    role: MemberRole = Field(
        default=MemberRole.ACCOUNT,
        sa_type=sa.Enum(
            MemberRole,
            name="member_role",
            native_enum=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        index=True,
    )
    status: MemberStatus = Field(
        default=MemberStatus.ACTIVE,
        sa_type=sa.Enum(
            MemberStatus,
            name="member_status",
            native_enum=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        index=True,
    )

    # Nome público na clínica (pode ser diferente do account.name privado)
    # Preenchido automaticamente do account.name na primeira vez, mas pode ser editado por admin
    name: str | None = Field(default=None, nullable=True)

    # Atributos customizados (JSON)
    attribute: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
