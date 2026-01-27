import os
from contextlib import contextmanager
from sqlmodel import create_engine, SQLModel, Session
from typing import Generator

# Importa psycopg para garantir que está disponível
try:
    import psycopg
except ImportError:
    raise ImportError("psycopg não está instalado. Execute: pip install psycopg[binary]")

# URL do banco de dados
# SQLAlchemy 2.0.45 usa psycopg2 por padrão, então usamos postgresql+psycopg2://
# ou apenas postgresql:// que detecta automaticamente
raw_url = os.getenv("DATABASE_URL", "postgresql://turna:turna@localhost:5433/turna")
# Se não tiver driver especificado, deixa como está (SQLAlchemy detecta)
DATABASE_URL = raw_url

# Engine singleton
# Força o uso do driver psycopg3
engine = create_engine(DATABASE_URL, echo=False)


def get_session() -> Generator[Session, None, None]:
    """Dependency do FastAPI para obter sessão do banco."""
    with Session(engine) as session:
        yield session


@contextmanager
def get_session_context() -> Generator[Session, None, None]:
    """Context manager para obter sessão do banco (uso fora de FastAPI Depends)."""
    with Session(engine) as session:
        yield session


def create_tables():
    """Cria todas as tabelas (útil para testes)."""
    SQLModel.metadata.create_all(engine)
