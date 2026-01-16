from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlmodel import Field

from app.model.base import BaseModel


class AuditLog(BaseModel, table=True):
    __tablename__ = "audit_log"

    # tenant_id pode ser NULL para eventos globais; para switch-tenant usamos o tenant "de origem".
    tenant_id: int | None = Field(default=None, foreign_key="tenant.id", index=True)

    actor_account_id: int = Field(foreign_key="account.id", index=True)
    membership_id: int | None = Field(default=None, foreign_key="membership.id", index=True)

    event_type: str = Field(index=True)
    data: dict[str, Any] | None = Field(default=None, sa_type=sa.JSON)
