from sqlmodel import SQLModel
from app.models import Tenant, User, Job


# Importa todos os modelos para que o SQLModel os registre
__all__ = ["Base"]


# Base para criar tabelas
Base = SQLModel.metadata
