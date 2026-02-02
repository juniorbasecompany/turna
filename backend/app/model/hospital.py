from sqlmodel import Field
from sqlalchemy import UniqueConstraint

from app.model.base import BaseModel


class Hospital(BaseModel, table=True):
    """Modelo Hospital - origem das demandas com prompt personalizado."""

    __tablename__ = "hospital"

    tenant_id: int = Field(foreign_key="tenant.id", index=True, nullable=False)
    name: str = Field(nullable=False)
    # Rótulo opcional; sem duplicação dentro do tenant quando preenchido
    label: str | None = Field(default=None, nullable=True, index=True)
    prompt: str | None = Field(default=None, nullable=True)
    color: str | None = Field(default=None, nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_hospital_tenant_name"),
    )
