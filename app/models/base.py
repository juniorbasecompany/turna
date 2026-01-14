from datetime import datetime
from sqlmodel import SQLModel, Field
from typing import Optional


class BaseModel(SQLModel):
    """Modelo base com campos comuns a todas as tabelas."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
