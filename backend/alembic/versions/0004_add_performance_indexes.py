"""Add composite performance indexes for core platform tables

Revision ID: 0004_add_performance_indexes
Revises: 0003_add_mfa_fields_to_users
Create Date: 2026-08-05 22:15:00.000000

"""

from typing import Sequence, Union
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_add_performance_indexes"
down_revision: Union[str, None] = "0003_add_mfa_fields_to_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add composite performance indexes."""
    # 1. Users table indexes
    op.create_index(
        "ix_users_org_role",
        "users",
        ["organization_id", "role"],
        unique=False,
    )
    op.create_index(
        "ix_users_org_active",
        "users",
        ["organization_id", "is_active"],
        unique=False,
    )

    # 2. Audit logs table indexes
    op.create_index(
        "ix_audit_logs_org_action",
        "audit_logs",
        ["organization_id", "action"],
        unique=False,
    )
    op.create_index(
        "ix_audit_logs_org_created",
        "audit_logs",
        ["organization_id", "created_at"],
        unique=False,
    )

    # 3. Refresh tokens table indexes
    op.create_index(
        "ix_refresh_tokens_user_revoked",
        "refresh_tokens",
        ["user_id", "is_revoked"],
        unique=False,
    )

    # 4. API keys table indexes
    op.create_index(
        "ix_api_keys_org_active",
        "api_keys",
        ["organization_id", "is_active"],
        unique=False,
    )


def downgrade() -> None:
    """Remove composite performance indexes."""
    op.drop_index("ix_api_keys_org_active", table_name="api_keys")
    op.drop_index("ix_refresh_tokens_user_revoked", table_name="refresh_tokens")
    op.drop_index("ix_audit_logs_org_created", table_name="audit_logs")
    op.drop_index("ix_audit_logs_org_action", table_name="audit_logs")
    op.drop_index("ix_users_org_active", table_name="users")
    op.drop_index("ix_users_org_role", table_name="users")
