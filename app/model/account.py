from sqlmodel import Field
from sqlalchemy import UniqueConstraint
from app.model.base import BaseModel


class Account(BaseModel, table=True):
    """Modelo Account - contas do sistema (tabela account no banco)."""

    __tablename__ = "account"

    email: str = Field(index=True)
    name: str
    # Observação: role "real" para autorização vive no Membership; aqui é legado/conveniência.
    role: str = Field(default="account")  # account, admin
    auth_provider: str = Field(default="google")  # google, etc.

    # Email globalmente único (um Account pode participar de múltiplos tenants via Membership)
    __table_args__ = (
        UniqueConstraint("email", name="uq_account_email"),
    )

