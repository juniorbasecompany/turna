from sqlmodel import Field
from sqlalchemy import UniqueConstraint

from app.model.base import BaseModel


class Professional(BaseModel, table=True):
    """Modelo Professional - profissionais que podem ser alocados nas escalas."""

    __tablename__ = "professional"

    tenant_id: int = Field(foreign_key="tenant.id", index=True, nullable=False)
    account_id: int | None = Field(
        foreign_key="account.id",
        index=True,
        nullable=True,
        default=None
    )
    name: str = Field(nullable=False, index=True)
    email: str = Field(nullable=False, index=True)
    phone: str | None = Field(default=None, nullable=True)
    notes: str | None = Field(default=None, nullable=True)
    active: bool = Field(default=True, nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_professional_tenant_name"),
    )
