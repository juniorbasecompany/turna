"""rename tables to singular

Revision ID: 0089abc12345
Revises: 0078efde8a31
Create Date: 2025-01-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0089abc12345'
down_revision: Union[str, None] = '0078efde8a31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Renomear tabelas na ordem correta (primeiro a que outras referenciam)

    # 1. Renomear tenants -> tenant (primeiro porque outras tabelas têm FK para ela)
    # PostgreSQL atualiza automaticamente as FKs que referenciam esta tabela
    op.rename_table('tenants', 'tenant')

    # 2. Descobrir e atualizar foreign keys que referenciam tenant ANTES de renomear outras tabelas
    conn = op.get_bind()

    # Descobrir nome da constraint FK de users.tenant_id
    result = conn.execute(sa.text("""
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'users'
        AND constraint_type = 'FOREIGN KEY'
        AND constraint_name LIKE '%tenant_id%'
    """))
    fk_users = result.scalar()
    if fk_users:
        op.drop_constraint(fk_users, 'users', type_='foreignkey')
        op.create_foreign_key('user_tenant_id_fkey', 'users', 'tenant', ['tenant_id'], ['id'])

    # Descobrir nome da constraint FK de jobs.tenant_id
    result = conn.execute(sa.text("""
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'jobs'
        AND constraint_type = 'FOREIGN KEY'
        AND constraint_name LIKE '%tenant_id%'
    """))
    fk_jobs = result.scalar()
    if fk_jobs:
        op.drop_constraint(fk_jobs, 'jobs', type_='foreignkey')
        op.create_foreign_key('job_tenant_id_fkey', 'jobs', 'tenant', ['tenant_id'], ['id'])

    # 3. Renomear users -> user
    op.rename_table('users', 'user')

    # 4. Renomear jobs -> job
    op.rename_table('jobs', 'job')

    # 5. Atualizar índices que referenciam nomes de tabelas
    # Índices de tenant
    op.execute(sa.text("ALTER INDEX ix_tenants_name RENAME TO ix_tenant_name"))
    op.execute(sa.text("ALTER INDEX ix_tenants_slug RENAME TO ix_tenant_slug"))

    # Índices de user
    op.execute(sa.text("ALTER INDEX ix_users_email RENAME TO ix_user_email"))
    op.execute(sa.text("ALTER INDEX ix_users_tenant_id RENAME TO ix_user_tenant_id"))

    # Índices de job
    op.execute(sa.text("ALTER INDEX ix_jobs_job_type RENAME TO ix_job_job_type"))
    op.execute(sa.text("ALTER INDEX ix_jobs_status RENAME TO ix_job_status"))
    op.execute(sa.text("ALTER INDEX ix_jobs_tenant_id RENAME TO ix_job_tenant_id"))


def downgrade() -> None:
    # Reverter na ordem inversa

    # 1. Reverter índices
    op.execute(sa.text("ALTER INDEX ix_job_tenant_id RENAME TO ix_jobs_tenant_id"))
    op.execute(sa.text("ALTER INDEX ix_job_status RENAME TO ix_jobs_status"))
    op.execute(sa.text("ALTER INDEX ix_job_job_type RENAME TO ix_jobs_job_type"))

    op.execute(sa.text("ALTER INDEX ix_user_tenant_id RENAME TO ix_users_tenant_id"))
    op.execute(sa.text("ALTER INDEX ix_user_email RENAME TO ix_users_email"))

    op.execute(sa.text("ALTER INDEX ix_tenant_slug RENAME TO ix_tenants_slug"))
    op.execute(sa.text("ALTER INDEX ix_tenant_name RENAME TO ix_tenants_name"))

    # 2. Renomear tabelas de volta (antes de atualizar FKs)
    op.rename_table('job', 'jobs')
    op.rename_table('user', 'users')

    # 3. Reverter foreign keys
    op.drop_constraint('job_tenant_id_fkey', 'jobs', type_='foreignkey')
    op.create_foreign_key('jobs_tenant_id_fkey', 'jobs', 'tenant', ['tenant_id'], ['id'])

    op.drop_constraint('user_tenant_id_fkey', 'users', type_='foreignkey')
    op.create_foreign_key('users_tenant_id_fkey', 'users', 'tenant', ['tenant_id'], ['id'])

    # 4. Renomear tenant por último
    op.rename_table('tenant', 'tenants')

    # 5. Atualizar FKs para referenciar tenants novamente
    op.drop_constraint('jobs_tenant_id_fkey', 'jobs', type_='foreignkey')
    op.create_foreign_key('jobs_tenant_id_fkey', 'jobs', 'tenants', ['tenant_id'], ['id'])

    op.drop_constraint('users_tenant_id_fkey', 'users', type_='foreignkey')
    op.create_foreign_key('users_tenant_id_fkey', 'users', 'tenants', ['tenant_id'], ['id'])
