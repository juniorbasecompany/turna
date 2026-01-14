import os
import sys
from pathlib import Path
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from sqlmodel import SQLModel

# Adiciona o diretório raiz do projeto ao Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Importa todos os modelos para que o SQLModel os registre
from app.model import Tenant, Account, Job, File

config = context.config
fileConfig(config.config_file_name)

def get_url() -> str:
    # Remove o prefixo +psycopg se existir, usa apenas postgresql://
    url = os.environ.get("DATABASE_URL", "postgresql://turna:turna@localhost:5433/turna")
    # Garante que não tenha o prefixo +psycopg que causa problemas
    if "+psycopg" in url:
        url = url.replace("+psycopg", "")
    return url

config.set_main_option("sqlalchemy.url", get_url())

# Metadata do SQLModel com todos os modelos
target_metadata = SQLModel.metadata

def run_migrations_offline():
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
