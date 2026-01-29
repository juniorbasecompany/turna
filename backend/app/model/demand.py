from datetime import datetime
from typing import Optional
import enum
import sqlalchemy as sa
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON, CheckConstraint

from app.model.base import BaseModel


class ScheduleStatus(str, enum.Enum):
    """Status da escala na Demand (DRAFT, PUBLISHED, ARCHIVED)."""
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class Demand(BaseModel, table=True):
    """Modelo Demand - demandas cirúrgicas extraídas de arquivos. Concentra também o estado da escala (status, result_data, PDF)."""

    __tablename__ = "demand"

    tenant_id: int = Field(foreign_key="tenant.id", index=True, nullable=False)
    hospital_id: Optional[int] = Field(foreign_key="hospital.id", index=True, nullable=True)
    job_id: Optional[int] = Field(foreign_key="job.id", index=True, nullable=True)
    # Member atribuído à demanda no momento do cálculo da escala (gravação ao gerar escala)
    member_id: Optional[int] = Field(default=None, foreign_key="member.id", index=True, nullable=True)

    # Campos principais (demanda)
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

    # Campos de escala (estado da escala na própria Demand)
    schedule_status: Optional[ScheduleStatus] = Field(
        default=None,
        sa_type=sa.Enum(
            ScheduleStatus,
            name="demand_schedule_status",
            native_enum=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        index=True,
        nullable=True,
    )
    schedule_name: Optional[str] = Field(default=None, nullable=True)
    schedule_version_number: int = Field(default=1, nullable=False)
    pdf_file_id: Optional[int] = Field(default=None, foreign_key="file.id", index=True, nullable=True)
    schedule_result_data: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    generated_at: Optional[datetime] = Field(
        default=None,
        sa_type=sa.DateTime(timezone=True),
        nullable=True,
    )
    published_at: Optional[datetime] = Field(
        default=None,
        sa_type=sa.DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint("end_time > start_time", name="ck_demand_end_after_start"),
    )
