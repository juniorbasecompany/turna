from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import UniqueConstraint
from app.models.base import BaseModel
from typing import Optional


class User(BaseModel, table=True):
    """Modelo User - usuários do sistema."""
    
    __tablename__ = "users"
    
    email: str = Field(index=True)
    name: str
    role: str = Field(default="user")  # user, admin
    tenant_id: int = Field(foreign_key="tenants.id", index=True)
    auth_provider: str = Field(default="google")  # google, etc.
    
    # Índice único em (email, tenant_id)
    __table_args__ = (
        UniqueConstraint("email", "tenant_id", name="uq_user_email_tenant"),
    )
