from sqlmodel import SQLModel, Field
from app.models.base import BaseModel


class Tenant(BaseModel, table=True):
    """Modelo Tenant - raiz do multi-tenant (não tem tenant_id)."""

    __tablename__ = "tenant"

    name: str = Field(index=True)
    slug: str = Field(unique=True, index=True)
