from sqlmodel import SQLModel, Field
from app.model.base import BaseModel


class Tenant(BaseModel, table=True):
    """Modelo Tenant - raiz do multi-tenant (não tem tenant_id)."""

    __tablename__ = "tenant"

    name: str = Field(index=True)
    label: str | None = Field(default=None, nullable=True, index=True)
    timezone: str = Field(default="America/Sao_Paulo")
    locale: str = Field(default="pt-BR")
    currency: str = Field(default="BRL")

    @property
    def display_name(self) -> str:
        label = (self.label or "").strip()
        return label or self.name
