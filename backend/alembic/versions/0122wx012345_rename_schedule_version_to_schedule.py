"""rename schedule_version table to schedule

Revision ID: 0122wx012345
Revises: 0121uv012345
Create Date: 2026-01-25 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0122wx012345"
down_revision: Union[str, None] = "0121uv012345"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Renomeia a tabela schedule_version para schedule e atualiza os índices.
    """
    # Renomear índices primeiro
    op.execute("ALTER INDEX IF EXISTS ix_schedule_version_tenant_id RENAME TO ix_schedule_tenant_id")
    op.execute("ALTER INDEX IF EXISTS ix_schedule_version_status RENAME TO ix_schedule_status")
    op.execute("ALTER INDEX IF EXISTS ix_schedule_version_job_id RENAME TO ix_schedule_job_id")
    op.execute("ALTER INDEX IF EXISTS ix_schedule_version_pdf_file_id RENAME TO ix_schedule_pdf_file_id")
    
    # Renomear a tabela
    op.execute("ALTER TABLE schedule_version RENAME TO schedule")


def downgrade() -> None:
    """
    Reverte a renomeação: schedule volta para schedule_version.
    """
    # Renomear a tabela de volta
    op.execute("ALTER TABLE schedule RENAME TO schedule_version")
    
    # Renomear índices de volta
    op.execute("ALTER INDEX IF EXISTS ix_schedule_tenant_id RENAME TO ix_schedule_version_tenant_id")
    op.execute("ALTER INDEX IF EXISTS ix_schedule_status RENAME TO ix_schedule_version_status")
    op.execute("ALTER INDEX IF EXISTS ix_schedule_job_id RENAME TO ix_schedule_version_job_id")
    op.execute("ALTER INDEX IF EXISTS ix_schedule_pdf_file_id RENAME TO ix_schedule_version_pdf_file_id")
