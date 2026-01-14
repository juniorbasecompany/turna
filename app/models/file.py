from datetime import datetime
from sqlmodel import SQLModel, Field
from app.models.base import BaseModel
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
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
