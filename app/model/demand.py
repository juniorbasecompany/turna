from datetime import datetime
from typing import Optional
import sqlalchemy as sa
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON, CheckConstraint

from app.model.base import BaseModel


class Demand(BaseModel, table=True):
    """Modelo Demand - demandas cirúrgicas extraídas de arquivos."""

    __tablename__ = "demand"

    tenant_id: int = Field(foreign_key="tenant.id", index=True, nullable=False)
    hospital_id: Optional[int] = Field(foreign_key="hospital.id", index=True, nullable=True)
    job_id: Optional[int] = Field(foreign_key="job.id", index=True, nullable=True)

    # Campos principais
    room: Optional[str] = Field(default=None, nullable=True)
    start_time: datetime = Field(
        sa_type=sa.DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    end_time: datetime = Field(
        sa_type=sa.DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    procedure: str = Field(nullable=False)
    anesthesia_type: Optional[str] = Field(default=None, nullable=True)
    complexity: Optional[str] = Field(default=None, nullable=True)
    skills: Optional[list[str]] = Field(default=None, sa_column=Column(JSON))
    priority: Optional[str] = Field(default=None, nullable=True)  # "Urgente" | "Emergência" | None
    is_pediatric: bool = Field(default=False, nullable=False, index=True)
    notes: Optional[str] = Field(default=None, nullable=True)
    source: Optional[dict] = Field(default=None, sa_column=Column(JSON))

    __table_args__ = (
        CheckConstraint("end_time > start_time", name="ck_demand_end_after_start"),
    )
