from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import UniqueConstraint
from app.model.base import BaseModel
from typing import Optional


class Account(BaseModel, table=True):
    """Modelo Account - contas do sistema (tabela account no banco)."""

    __tablename__ = "account"

    email: str = Field(index=True)
    name: str
    role: str = Field(default="user")  # user, admin
    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    auth_provider: str = Field(default="google")  # google, etc.

    # Índice único em (email, tenant_id)
    __table_args__ = (
        UniqueConstraint("email", "tenant_id", name="uq_account_email_tenant"),
    )
