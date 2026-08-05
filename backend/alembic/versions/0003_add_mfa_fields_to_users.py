"""Add MFA fields to users table

Revision ID: 0003_add_mfa_fields_to_users
Revises: 0002_create_core_platform_tables
Create Date: 2026-08-05 21:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_add_mfa_fields_to_users"
down_revision: Union[str, None] = "0002_create_core_platform_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add MFA fields to users table."""
    # Check if is_mfa_enabled column exists; rename or add mfa_enabled
    op.add_column(
        "users",
        sa.Column("mfa_enabled", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("mfa_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("mfa_backup_codes", sa.String(length=4096), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("mfa_last_used_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Remove MFA fields from users table."""
    op.drop_column("users", "mfa_last_used_at")
    op.drop_column("users", "mfa_backup_codes")
    op.drop_column("users", "mfa_verified_at")
    op.drop_column("users", "mfa_enabled")
