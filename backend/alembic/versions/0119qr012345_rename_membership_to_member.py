"""rename membership to member

Revision ID: 0119qr012345
Revises: 0118op012345
Create Date: 2026-01-22 03:45:46.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "0119qr012345"
down_revision: Union[str, None] = "0118op012345"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Renomeia membership para member em todo o banco de dados.
    
    Passos:
    1. Verificar e renomear enums membership_role e membership_status (se existirem)
    2. Renomear tabela membership para member (PRIMEIRO!)
    3. Renomear foreign keys e colunas membership_id para member_id em outras tabelas
    4. Renomear constraint única em profile
    5. Renomear índices
    """
    
    # 1. Verificar e renomear enums (se existirem)
    # Verificar se os enums existem antes de tentar renomeá-los
    conn = op.get_bind()
    
    # Verificar membership_role
    result = conn.execute(text("SELECT typname FROM pg_type WHERE typname = 'membership_role'"))
    has_membership_role = result.fetchone() is not None
    
    result = conn.execute(text("SELECT typname FROM pg_type WHERE typname = 'member_role'"))
    has_member_role = result.fetchone() is not None
    
    if has_membership_role:
        op.execute("ALTER TYPE membership_role RENAME TO member_role")
    elif not has_member_role:
        # Se não existe nenhum dos dois, criar o enum member_role
        op.execute("CREATE TYPE member_role AS ENUM ('admin', 'account')")
    
    # Verificar membership_status
    result = conn.execute(text("SELECT typname FROM pg_type WHERE typname = 'membership_status'"))
    has_membership_status = result.fetchone() is not None
    
    result = conn.execute(text("SELECT typname FROM pg_type WHERE typname = 'member_status'"))
    has_member_status = result.fetchone() is not None
    
    if has_membership_status:
        op.execute("ALTER TYPE membership_status RENAME TO member_status")
    elif not has_member_status:
        # Se não existe nenhum dos dois, criar o enum member_status
        op.execute("CREATE TYPE member_status AS ENUM ('PENDING', 'ACTIVE', 'REJECTED', 'REMOVED')")
    
    # 2. Renomear a tabela membership para member (DEVE SER FEITO ANTES DE CRIAR FOREIGN KEYS)
    op.rename_table("membership", "member")
    
    # 3. Renomear foreign keys e colunas membership_id para member_id em outras tabelas
    # Profile
    op.drop_constraint("profile_membership_id_fkey", "profile", type_="foreignkey")
    op.drop_index(op.f("ix_profile_membership_id"), table_name="profile")
    op.alter_column("profile", "membership_id", new_column_name="member_id")
    op.create_foreign_key("profile_member_id_fkey", "profile", "member", ["member_id"], ["id"])
    op.create_index(op.f("ix_profile_member_id"), "profile", ["member_id"], unique=False)
    
    # Renomear constraint única em profile
    op.drop_constraint("uq_profile_tenant_membership_hospital", "profile", type_="unique")
    op.create_unique_constraint("uq_profile_tenant_member_hospital", "profile", ["tenant_id", "member_id", "hospital_id"])
    
    # AuditLog
    op.drop_constraint("audit_log_membership_id_fkey", "audit_log", type_="foreignkey")
    op.drop_index(op.f("ix_audit_log_membership_id"), table_name="audit_log")
    op.alter_column("audit_log", "membership_id", new_column_name="member_id")
    op.create_foreign_key("audit_log_member_id_fkey", "audit_log", "member", ["member_id"], ["id"])
    op.create_index(op.f("ix_audit_log_member_id"), "audit_log", ["member_id"], unique=False)
    
    # 4. Renomear índices na tabela member (já renomeada)
    # Usar DROP INDEX IF EXISTS para evitar erros se o índice não existir
    op.execute("DROP INDEX IF EXISTS ix_membership_tenant_id")
    op.execute("DROP INDEX IF EXISTS ix_membership_account_id")
    op.execute("DROP INDEX IF EXISTS ix_membership_email")
    op.execute("DROP INDEX IF EXISTS ix_membership_role")
    op.execute("DROP INDEX IF EXISTS ix_membership_status")
    
    # 5. Recriar índices com novos nomes
    op.create_index(op.f("ix_member_tenant_id"), "member", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_member_account_id"), "member", ["account_id"], unique=False)
    op.create_index(op.f("ix_member_email"), "member", ["email"], unique=False)
    op.create_index(op.f("ix_member_role"), "member", ["role"], unique=False)
    op.create_index(op.f("ix_member_status"), "member", ["status"], unique=False)
    
    # Renomear foreign keys da tabela member
    op.drop_constraint("membership_tenant_id_fkey", "member", type_="foreignkey")
    op.drop_constraint("membership_account_id_fkey", "member", type_="foreignkey")
    op.create_foreign_key("member_tenant_id_fkey", "member", "tenant", ["tenant_id"], ["id"])
    op.create_foreign_key("member_account_id_fkey", "member", "account", ["account_id"], ["id"])


def downgrade() -> None:
    """
    Reverter renomeação: member -> membership
    """
    
    # 1. Renomear foreign keys e colunas member_id para membership_id (ANTES de renomear a tabela)
    # Profile
    op.drop_constraint("profile_member_id_fkey", "profile", type_="foreignkey")
    op.drop_index(op.f("ix_profile_member_id"), table_name="profile")
    op.alter_column("profile", "member_id", new_column_name="membership_id")
    op.create_foreign_key("profile_membership_id_fkey", "profile", "member", ["membership_id"], ["id"])
    op.create_index(op.f("ix_profile_membership_id"), "profile", ["membership_id"], unique=False)
    
    # Renomear constraint única em profile
    op.drop_constraint("uq_profile_tenant_member_hospital", "profile", type_="unique")
    op.create_unique_constraint("uq_profile_tenant_membership_hospital", "profile", ["tenant_id", "membership_id", "hospital_id"])
    
    # AuditLog
    op.drop_constraint("audit_log_member_id_fkey", "audit_log", type_="foreignkey")
    op.drop_index(op.f("ix_audit_log_member_id"), table_name="audit_log")
    op.alter_column("audit_log", "member_id", new_column_name="membership_id")
    op.create_foreign_key("audit_log_membership_id_fkey", "audit_log", "member", ["membership_id"], ["id"])
    op.create_index(op.f("ix_audit_log_membership_id"), "audit_log", ["membership_id"], unique=False)
    
    # 2. Renomear índices na tabela member antes de renomear a tabela
    # Usar DROP INDEX IF EXISTS para evitar erros se o índice não existir
    op.execute("DROP INDEX IF EXISTS ix_member_tenant_id")
    op.execute("DROP INDEX IF EXISTS ix_member_account_id")
    op.execute("DROP INDEX IF EXISTS ix_member_email")
    op.execute("DROP INDEX IF EXISTS ix_member_role")
    op.execute("DROP INDEX IF EXISTS ix_member_status")
    
    # 3. Renomear a tabela member para membership
    op.rename_table("member", "membership")
    
    # 4. Recriar índices com nomes antigos
    op.create_index(op.f("ix_membership_tenant_id"), "membership", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_membership_account_id"), "membership", ["account_id"], unique=False)
    op.create_index(op.f("ix_membership_email"), "membership", ["email"], unique=False)
    op.create_index(op.f("ix_membership_role"), "membership", ["role"], unique=False)
    op.create_index(op.f("ix_membership_status"), "membership", ["status"], unique=False)
    
    # Renomear foreign keys da tabela membership
    op.drop_constraint("member_tenant_id_fkey", "membership", type_="foreignkey")
    op.drop_constraint("member_account_id_fkey", "membership", type_="foreignkey")
    op.create_foreign_key("membership_tenant_id_fkey", "membership", "tenant", ["tenant_id"], ["id"])
    op.create_foreign_key("membership_account_id_fkey", "membership", "account", ["account_id"], ["id"])
    
    # 5. Renomear enums de volta (por último, se existirem)
    conn = op.get_bind()
    
    result = conn.execute(text("SELECT typname FROM pg_type WHERE typname = 'member_role'"))
    if result.fetchone() is not None:
        op.execute("ALTER TYPE member_role RENAME TO membership_role")
    
    result = conn.execute(text("SELECT typname FROM pg_type WHERE typname = 'member_status'"))
    if result.fetchone() is not None:
        op.execute("ALTER TYPE member_status RENAME TO membership_status")
