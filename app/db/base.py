from sqlmodel import SQLModel
from app.model import Tenant, Account, Member, AuditLog, Job, File, ScheduleVersion, Hospital, Demand


# Importa todos os modelos para que o SQLModel os registre
__all__ = ["Base"]


# Base para criar tabelas
Base = SQLModel.metadata
