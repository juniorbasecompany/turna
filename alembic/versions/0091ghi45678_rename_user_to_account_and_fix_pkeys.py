"""rename user to account and fix primary key constraints

Revision ID: 0091ghi45678
Revises: 0089abc12345
Create Date: 2025-01-15 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0091ghi45678'
down_revision: Union[str, None] = '0089abc12345'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. Renomear constraints de chave primária para singular
    # tenant_pkey (pode estar como tenants_pkey ou tenant_pkey)
    result = conn.execute(sa.text("""
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'tenant'
        AND constraint_type = 'PRIMARY KEY'
    """))
    tenant_pkey = result.scalar()
    if tenant_pkey and tenant_pkey != 'tenant_pkey':
        op.execute(sa.text(f"ALTER TABLE tenant RENAME CONSTRAINT {tenant_pkey} TO tenant_pkey"))

    # users_pkey -> account_pkey (renomear antes de renomear a tabela)
    result = conn.execute(sa.text("""
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'user'
        AND constraint_type = 'PRIMARY KEY'
    """))
    user_pkey = result.scalar()
    if user_pkey:
        if user_pkey == 'users_pkey':
            # Se ainda está no plural, renomear para account_pkey
            op.execute(sa.text('ALTER TABLE "user" RENAME CONSTRAINT users_pkey TO account_pkey'))
        elif user_pkey != 'account_pkey':
            # Se tem outro nome, renomear para account_pkey
            op.execute(sa.text(f'ALTER TABLE "user" RENAME CONSTRAINT {user_pkey} TO account_pkey'))

    # jobs_pkey -> job_pkey
    result = conn.execute(sa.text("""
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'job'
        AND constraint_type = 'PRIMARY KEY'
    """))
    job_pkey = result.scalar()
    if job_pkey and job_pkey != 'job_pkey':
        op.execute(sa.text(f"ALTER TABLE job RENAME CONSTRAINT {job_pkey} TO job_pkey"))

    # 2. Descobrir e atualizar foreign keys que referenciam user ANTES de renomear a tabela
    # Descobrir nome da constraint FK de job que pode referenciar user (se houver)
    # Por enquanto, vamos focar nas FKs que referenciam user.tenant_id
    result = conn.execute(sa.text("""
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'user'
        AND constraint_type = 'FOREIGN KEY'
        AND constraint_name LIKE '%tenant_id%'
    """))
    fk_user_tenant = result.scalar()
    if fk_user_tenant and fk_user_tenant != 'account_tenant_id_fkey':
        op.drop_constraint(fk_user_tenant, 'user', type_='foreignkey')
        op.create_foreign_key('account_tenant_id_fkey', 'user', 'tenant', ['tenant_id'], ['id'])

    # 3. Renomear constraint única de user
    result = conn.execute(sa.text("""
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'user'
        AND constraint_type = 'UNIQUE'
        AND constraint_name LIKE '%email%'
    """))
    uq_user_email = result.scalar()
    if uq_user_email and uq_user_email != 'uq_account_email_tenant':
        op.execute(sa.text(f"ALTER TABLE \"user\" RENAME CONSTRAINT {uq_user_email} TO uq_account_email_tenant"))

    # 4. Renomear índices relacionados a user
    # Verificar se os índices existem antes de renomear
    result = conn.execute(sa.text("""
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'user' AND indexname = 'ix_user_email'
    """))
    if result.scalar():
        op.execute(sa.text("ALTER INDEX ix_user_email RENAME TO ix_account_email"))

    result = conn.execute(sa.text("""
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'user' AND indexname = 'ix_user_tenant_id'
    """))
    if result.scalar():
        op.execute(sa.text("ALTER INDEX ix_user_tenant_id RENAME TO ix_account_tenant_id"))

    # 5. Renomear a tabela user para account (user é palavra reservada no PostgreSQL)
    op.rename_table('user', 'account')


def downgrade() -> None:
    conn = op.get_bind()

    # 1. Renomear a tabela account de volta para user
    op.rename_table('account', 'user')

    # 2. Reverter índices
    result = conn.execute(sa.text("""
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'user' AND indexname = 'ix_account_tenant_id'
    """))
    if result.scalar():
        op.execute(sa.text("ALTER INDEX ix_account_tenant_id RENAME TO ix_user_tenant_id"))

    result = conn.execute(sa.text("""
        SELECT indexname
        FROM pg_indexes
        WHERE tablename = 'user' AND indexname = 'ix_account_email'
    """))
    if result.scalar():
        op.execute(sa.text("ALTER INDEX ix_account_email RENAME TO ix_user_email"))

    # 3. Reverter constraint única
    op.execute(sa.text("ALTER TABLE \"user\" RENAME CONSTRAINT uq_account_email_tenant TO uq_user_email_tenant"))

    # 4. Reverter foreign key
    op.drop_constraint('account_tenant_id_fkey', 'user', type_='foreignkey')
    result = conn.execute(sa.text("""
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'user'
        AND constraint_type = 'FOREIGN KEY'
        AND constraint_name LIKE '%tenant_id%'
    """))
    # Se não encontrar, criar com nome padrão
    op.create_foreign_key('user_tenant_id_fkey', 'user', 'tenant', ['tenant_id'], ['id'])

    # 5. Reverter constraints de chave primária
    result = conn.execute(sa.text("""
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'user'
        AND constraint_type = 'PRIMARY KEY'
    """))
    current_pkey = result.scalar()
    if current_pkey == 'account_pkey':
        op.execute(sa.text('ALTER TABLE "user" RENAME CONSTRAINT account_pkey TO users_pkey'))

    result = conn.execute(sa.text("""
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'job'
        AND constraint_type = 'PRIMARY KEY'
    """))
    current_job_pkey = result.scalar()
    if current_job_pkey == 'job_pkey':
        op.execute(sa.text("ALTER TABLE job RENAME CONSTRAINT job_pkey TO jobs_pkey"))

    result = conn.execute(sa.text("""
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = 'tenant'
        AND constraint_type = 'PRIMARY KEY'
    """))
    current_tenant_pkey = result.scalar()
    if current_tenant_pkey == 'tenant_pkey':
        op.execute(sa.text("ALTER TABLE tenant RENAME CONSTRAINT tenant_pkey TO tenants_pkey"))
