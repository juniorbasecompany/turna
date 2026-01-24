"""make timestamps timestamptz (UTC)

Revision ID: 0093mno12345
Revises: 0092jkl78901
Create Date: 2026-01-14 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0093mno12345"
down_revision: Union[str, None] = "0092jkl78901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Converte timestamp without time zone -> timestamptz assumindo que os valores atuais estão em UTC.
    op.execute(sa.text("ALTER TABLE tenant ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'"))
    op.execute(sa.text("ALTER TABLE tenant ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'"))

    op.execute(sa.text("ALTER TABLE account ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'"))
    op.execute(sa.text("ALTER TABLE account ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'"))

    op.execute(sa.text("ALTER TABLE job ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'"))
    op.execute(sa.text("ALTER TABLE job ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'"))
    op.execute(sa.text("ALTER TABLE job ALTER COLUMN completed_at TYPE TIMESTAMPTZ USING completed_at AT TIME ZONE 'UTC'"))

    op.execute(sa.text("ALTER TABLE file ALTER COLUMN uploaded_at TYPE TIMESTAMPTZ USING uploaded_at AT TIME ZONE 'UTC'"))
    op.execute(sa.text("ALTER TABLE file ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC'"))
    op.execute(sa.text("ALTER TABLE file ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC'"))


def downgrade() -> None:
    # Reverte timestamptz -> timestamp without time zone mantendo UTC.
    op.execute(sa.text("ALTER TABLE file ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'"))
    op.execute(sa.text("ALTER TABLE file ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'"))
    op.execute(sa.text("ALTER TABLE file ALTER COLUMN uploaded_at TYPE TIMESTAMP WITHOUT TIME ZONE USING uploaded_at AT TIME ZONE 'UTC'"))

    op.execute(sa.text("ALTER TABLE job ALTER COLUMN completed_at TYPE TIMESTAMP WITHOUT TIME ZONE USING completed_at AT TIME ZONE 'UTC'"))
    op.execute(sa.text("ALTER TABLE job ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'"))
    op.execute(sa.text("ALTER TABLE job ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'"))

    op.execute(sa.text("ALTER TABLE account ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'"))
    op.execute(sa.text("ALTER TABLE account ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'"))

    op.execute(sa.text("ALTER TABLE tenant ALTER COLUMN updated_at TYPE TIMESTAMP WITHOUT TIME ZONE USING updated_at AT TIME ZONE 'UTC'"))
    op.execute(sa.text("ALTER TABLE tenant ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE USING created_at AT TIME ZONE 'UTC'"))

