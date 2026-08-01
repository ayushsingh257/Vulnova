"""enable postgresql uuid and vector extensions

Revision ID: 0001_enable_postgresql_extensions
Revises:
Create Date: 2026-08-01 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_enable_postgresql_extensions"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable uuid-ossp and pgvector extensions in PostgreSQL."""
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector";')


def downgrade() -> None:
    """Drop vector and uuid-ossp extensions."""
    op.execute('DROP EXTENSION IF EXISTS "vector";')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp";')
