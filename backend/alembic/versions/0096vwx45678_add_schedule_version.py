"""add schedule_version table

Revision ID: 0096vwx45678
Revises: 0095stu34567
Create Date: 2026-01-15 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "0096vwx45678"
down_revision: Union[str, None] = "0095stu34567"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "schedule_version",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False, server_default="Schedule"),
        sa.Column("period_start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="DRAFT"),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("pdf_file_id", sa.Integer(), nullable=True),
        sa.Column("result_data", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenant.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["job.id"]),
        sa.ForeignKeyConstraint(["pdf_file_id"], ["file.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_schedule_version_tenant_id"), "schedule_version", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_schedule_version_status"), "schedule_version", ["status"], unique=False)
    op.create_index(op.f("ix_schedule_version_job_id"), "schedule_version", ["job_id"], unique=False)
    op.create_index(op.f("ix_schedule_version_pdf_file_id"), "schedule_version", ["pdf_file_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_schedule_version_pdf_file_id"), table_name="schedule_version")
    op.drop_index(op.f("ix_schedule_version_job_id"), table_name="schedule_version")
    op.drop_index(op.f("ix_schedule_version_status"), table_name="schedule_version")
    op.drop_index(op.f("ix_schedule_version_tenant_id"), table_name="schedule_version")
    op.drop_table("schedule_version")

