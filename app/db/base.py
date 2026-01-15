from sqlmodel import SQLModel
from app.model import Tenant, Account, Job, File, ScheduleVersion


# Importa todos os modelos para que o SQLModel os registre
__all__ = ["Base"]


# Base para criar tabelas
Base = SQLModel.metadata
