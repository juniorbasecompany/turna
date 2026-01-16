from sqlmodel import Field
from sqlalchemy import UniqueConstraint
from app.model.base import BaseModel
from typing import Optional


class Account(BaseModel, table=True):
    """Modelo Account - contas do sistema (tabela account no banco)."""

    __tablename__ = "account"

    email: str = Field(index=True)
    name: str
    role: str = Field(default="user")  # user, admin
    auth_provider: str = Field(default="google")  # google, etc.

    # Email globalmente único (um Account pode participar de múltiplos tenants via Membership)
    __table_args__ = (
        UniqueConstraint("email", name="uq_account_email"),
    )
