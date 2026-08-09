"""enable postgresql uuid and vector extensions

Revision ID: 0001_enable_postgresql_extensions
Revises:
Create Date: 2026-08-01 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_enable_pg_extensions"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable uuid-ossp and pgvector extensions in PostgreSQL."""
    conn = op.get_bind()
    try:
        conn.exec_driver_sql('SAVEPOINT s1;')
        conn.exec_driver_sql('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
        conn.exec_driver_sql('RELEASE SAVEPOINT s1;')
    except Exception:
        conn.exec_driver_sql('ROLLBACK TO SAVEPOINT s1;')
    try:
        conn.exec_driver_sql('SAVEPOINT s2;')
        conn.exec_driver_sql('CREATE EXTENSION IF NOT EXISTS "vector";')
        conn.exec_driver_sql('RELEASE SAVEPOINT s2;')
    except Exception:
        conn.exec_driver_sql('ROLLBACK TO SAVEPOINT s2;')


def downgrade() -> None:
    """Drop vector and uuid-ossp extensions."""
    op.execute('DROP EXTENSION IF EXISTS "vector";')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp";')
