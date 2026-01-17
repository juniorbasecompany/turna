from datetime import datetime, timezone
from typing import Optional

import sqlalchemy as sa
from sqlmodel import SQLModel, Field, Column

from app.model.base import utc_now


class FileBase(SQLModel):
    """Modelo base para File - sem updated_at (apenas id e created_at)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_type=sa.DateTime(timezone=True),
        nullable=False,
    )


class File(FileBase, table=True):
    """Modelo File - metadados de arquivos armazenados no MinIO/S3."""

    __tablename__ = "file"

    tenant_id: int = Field(foreign_key="tenant.id", index=True)
    hospital_id: int = Field(foreign_key="hospital.id", index=True, nullable=False)
    filename: str = Field(index=True)
    content_type: str
    s3_key: str = Field(unique=True, index=True)
    s3_url: str
    file_size: int  # Tamanho em bytes
