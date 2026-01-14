from datetime import datetime

import sqlalchemy as sa
from sqlmodel import SQLModel, Field, Column

from app.model.base import BaseModel, utc_now
from typing import Optional


class File(BaseModel, table=True):
    """Modelo File - metadados de arquivos armazenados no MinIO/S3."""

    __tablename__ = "file"

    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    filename: str = Field(index=True)
    content_type: str
    s3_key: str = Field(unique=True, index=True)
    s3_url: str
    file_size: int  # Tamanho em bytes
    uploaded_at: datetime = Field(
        default_factory=utc_now,
        sa_type=sa.DateTime(timezone=True),
        nullable=False,
    )
