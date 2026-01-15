from datetime import datetime
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
import sqlalchemy as sa
from app.model.base import BaseModel
from typing import Optional
import enum


class JobType(str, enum.Enum):
    PING = "PING"
    # Nome no singular para aderir à diretiva; valor mantido por compatibilidade com dados existentes.
    EXTRACT_DEMAND = "EXTRACT_DEMAND"
    GENERATE_SCHEDULE = "GENERATE_SCHEDULE"


class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Job(BaseModel, table=True):
    """Modelo Job - jobs assíncronos processados pelo Arq."""

    __tablename__ = "job"

    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    job_type: JobType = Field(index=True)
    status: JobStatus = Field(default=JobStatus.PENDING, index=True)
    input_data: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    result_data: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    error_message: Optional[str] = None
    started_at: Optional[datetime] = Field(
        default=None,
        sa_type=sa.DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        sa_type=sa.DateTime(timezone=True),
        nullable=True,
    )
