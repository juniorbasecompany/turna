"""set job foreign keys to ON DELETE SET NULL

Revision ID: 0123ab456789
Revises: 0122wx012345
Create Date: 2026-01-26 05:19:03.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0123ab456789"
down_revision: Union[str, None] = "0122wx012345"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Altera todas as foreign keys que referenciam job.id para usar ON DELETE SET NULL.
    Isso permite excluir jobs sem violar constraints, definindo job_id como NULL nas tabelas relacionadas.
    """
    # Tabela schedule
    # Descobrir o nome da constraint dinamicamente e recriar com ON DELETE SET NULL
    op.execute("""
        DO $$
        DECLARE
            constraint_name TEXT;
            attnum_val SMALLINT;
        BEGIN
            -- Obter o attnum do campo job_id
            SELECT attnum INTO attnum_val
            FROM pg_attribute
            WHERE attrelid = 'schedule'::regclass
            AND attname = 'job_id';
            
            -- Encontrar o nome da constraint para schedule.job_id
            SELECT conname INTO constraint_name
            FROM pg_constraint
            WHERE conrelid = 'schedule'::regclass
            AND conkey = ARRAY[attnum_val]
            AND contype = 'f';
            
            -- Dropar constraint se existir
            IF constraint_name IS NOT NULL THEN
                EXECUTE format('ALTER TABLE schedule DROP CONSTRAINT %I', constraint_name);
            END IF;
            
            -- Recriar com ON DELETE SET NULL
            ALTER TABLE schedule
            ADD CONSTRAINT schedule_job_id_fkey
            FOREIGN KEY (job_id) REFERENCES job(id) ON DELETE SET NULL;
        END $$;
    """)

    # Tabela demand
    # Descobrir o nome da constraint dinamicamente e recriar com ON DELETE SET NULL
    op.execute("""
        DO $$
        DECLARE
            constraint_name TEXT;
            attnum_val SMALLINT;
        BEGIN
            -- Obter o attnum do campo job_id
            SELECT attnum INTO attnum_val
            FROM pg_attribute
            WHERE attrelid = 'demand'::regclass
            AND attname = 'job_id';
            
            -- Encontrar o nome da constraint para demand.job_id
            SELECT conname INTO constraint_name
            FROM pg_constraint
            WHERE conrelid = 'demand'::regclass
            AND conkey = ARRAY[attnum_val]
            AND contype = 'f';
            
            -- Dropar constraint se existir
            IF constraint_name IS NOT NULL THEN
                EXECUTE format('ALTER TABLE demand DROP CONSTRAINT %I', constraint_name);
            END IF;
            
            -- Recriar com ON DELETE SET NULL
            ALTER TABLE demand
            ADD CONSTRAINT demand_job_id_fkey
            FOREIGN KEY (job_id) REFERENCES job(id) ON DELETE SET NULL;
        END $$;
    """)


def downgrade() -> None:
    """
    Reverte as foreign keys para o comportamento padrão (sem ON DELETE SET NULL).
    """
    # Tabela schedule
    op.execute("""
        ALTER TABLE schedule
        DROP CONSTRAINT IF EXISTS schedule_job_id_fkey;
        
        ALTER TABLE schedule
        ADD CONSTRAINT schedule_job_id_fkey
        FOREIGN KEY (job_id) REFERENCES job(id);
    """)

    # Tabela demand
    op.execute("""
        ALTER TABLE demand
        DROP CONSTRAINT IF EXISTS demand_job_id_fkey;
        
        ALTER TABLE demand
        ADD CONSTRAINT demand_job_id_fkey
        FOREIGN KEY (job_id) REFERENCES job(id);
    """)
