from typing import Optional
from sqlmodel import Field, Column
from sqlalchemy import JSON, UniqueConstraint

from app.model.base import BaseModel


class Profile(BaseModel, table=True):
    """Modelo Profile - perfis de usuários com atributos customizados."""

    __tablename__ = "profile"

    tenant_id: int = Field(foreign_key="tenant.id", index=True, nullable=False)
    membership_id: int = Field(foreign_key="membership.id", index=True, nullable=False)
    hospital_id: Optional[int] = Field(foreign_key="hospital.id", index=True, nullable=True, default=None)
    attribute: dict = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "membership_id", "hospital_id", name="uq_profile_tenant_membership_hospital"),
    )
