from datetime import datetime
from typing import Optional
import enum

import sqlalchemy as sa
from sqlalchemy import JSON
from sqlmodel import Field, Column

from app.model.base import BaseModel


class ScheduleStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class Schedule(BaseModel, table=True):
    """
    Escala gerada.

    Observações:
      - `period_start_at` / `period_end_at` representam intervalo meio-aberto [start, end)
      - `generated_at` e `published_at` seguem diretiva `_at` com timestamptz
      - `hospital_id` é obrigatório; cada escala pertence a um hospital
    """

    __tablename__ = "schedule"

    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    hospital_id: int = Field(foreign_key="hospital.id", index=True, nullable=False)

    name: str = Field(default="Schedule")
    period_start_at: datetime = Field(
        sa_type=sa.DateTime(timezone=True),
        nullable=False,
    )
    period_end_at: datetime = Field(
        sa_type=sa.DateTime(timezone=True),
        nullable=False,
    )

    status: ScheduleStatus = Field(
        default=ScheduleStatus.DRAFT,
        sa_type=sa.Enum(
            ScheduleStatus,
            name="schedule_status",
            native_enum=False,
            values_callable=lambda e: [m.value for m in e],
        ),
        index=True,
    )
    version_number: int = Field(default=1)

    job_id: Optional[int] = Field(default=None, foreign_key="job.id", index=True)
    pdf_file_id: Optional[int] = Field(default=None, foreign_key="file.id", index=True)

    result_data: Optional[dict] = Field(default=None, sa_column=Column(JSON))

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

