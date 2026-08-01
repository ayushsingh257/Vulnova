"""Create core platform tables: organizations, users, refresh_tokens, api_keys, audit_logs

Revision ID: 0002_create_core_platform_tables
Revises: 0001_enable_postgresql_extensions
Create Date: 2026-08-01 18:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "0002_create_core_platform_tables"
down_revision: Union[str, None] = "0001_enable_postgresql_extensions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create core platform tables for multi-tenancy, authentication, API keys, and audit logging."""
    # 1. Organizations
    op.create_table(
        "organizations",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False, unique=True),
        sa.Column(
            "plan_tier",
            sa.String(length=50),
            nullable=False,
            server_default="ENTERPRISE_TRIAL",
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_organizations_slug", "organizations", ["slug"], unique=True)

    # 2. Users
    op.create_table(
        "users",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.String(length=50),
            nullable=False,
            server_default="SECURITY_ANALYST",
        ),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "is_mfa_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("mfa_secret", sa.String(length=255), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_users_org_id", "users", ["organization_id"])
    op.create_index("idx_users_email", "users", ["email"], unique=True)

    # 3. Refresh Tokens
    op.create_table(
        "refresh_tokens",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("family_id", UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False, unique=True),
        sa.Column(
            "is_revoked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_refresh_tokens_user", "refresh_tokens", ["user_id"])
    op.create_index("idx_refresh_tokens_family", "refresh_tokens", ["family_id"])
    op.create_index(
        "idx_refresh_tokens_hash", "refresh_tokens", ["token_hash"], unique=True
    )

    # 4. API Keys
    op.create_table(
        "api_keys",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("key_prefix", sa.String(length=8), nullable=False),
        sa.Column("key_hash", sa.String(length=255), nullable=False, unique=True),
        sa.Column(
            "scopes", sa.JSON(), nullable=False, server_default='["read", "write"]'
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("idx_api_keys_org", "api_keys", ["organization_id"])
    op.create_index("idx_api_keys_prefix", "api_keys", ["key_prefix"])
    op.create_index("idx_api_keys_hash", "api_keys", ["key_hash"], unique=True)

    # 5. Audit Logs
    op.create_table(
        "audit_logs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "actor_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column("client_ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_audit_logs_org_action", "audit_logs", ["organization_id", "action"]
    )
    op.create_index(
        "idx_audit_logs_created_at",
        "audit_logs",
        [sa.text("created_at DESC")],
    )


def downgrade() -> None:
    """Drop core platform tables in reverse order of creation."""
    op.drop_index("idx_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("idx_audit_logs_org_action", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("idx_api_keys_hash", table_name="api_keys")
    op.drop_index("idx_api_keys_prefix", table_name="api_keys")
    op.drop_index("idx_api_keys_org", table_name="api_keys")
    op.drop_table("api_keys")

    op.drop_index("idx_refresh_tokens_hash", table_name="refresh_tokens")
    op.drop_index("idx_refresh_tokens_family", table_name="refresh_tokens")
    op.drop_index("idx_refresh_tokens_user", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    op.drop_index("idx_users_email", table_name="users")
    op.drop_index("idx_users_org_id", table_name="users")
    op.drop_table("users")

    op.drop_index("idx_organizations_slug", table_name="organizations")
    op.drop_table("organizations")
