"""Create enterprise secrets vault tables: secret_vault_entries, secret_rotation_policies, and secret_access_policies

Revision ID: 0010_create_secret_vault_tables
Revises: 0009_create_plugin_security_tables
Create Date: 2026-08-09 17:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

# revision identifiers, used by Alembic.
revision: str = "0010_create_secret_vault_tables"
down_revision: Union[str, None] = "0009_create_plugin_security_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create secret vault and KMS governance tables for Phase 12.8."""
    # 1. secret_vault_entries
    op.create_table(
        "secret_vault_entries",
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
            index=True,
        ),
        sa.Column("secret_name", sa.String(255), nullable=False, index=True),
        sa.Column(
            "secret_type", sa.String(50), nullable=False, server_default="GENERIC"
        ),
        sa.Column(
            "provider", sa.String(50), nullable=False, server_default="local"
        ),
        sa.Column("kek_id", sa.String(255), nullable=False),
        sa.Column("encrypted_dek_hex", sa.Text(), nullable=False),
        sa.Column("encrypted_payload_hex", sa.Text(), nullable=False),
        sa.Column("nonce_hex", sa.String(64), nullable=False),
        sa.Column("tag_hex", sa.String(64), nullable=False),
        sa.Column(
            "key_version", sa.Integer(), nullable=False, server_default="1"
        ),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="ACTIVE",
            index=True,
        ),
        sa.Column("metadata_json", JSON, nullable=False, server_default="{}"),
        sa.Column("last_rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "expires_at", sa.DateTime(timezone=True), nullable=True, index=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_secret_vault_org_name",
        "secret_vault_entries",
        ["organization_id", "secret_name"],
        unique=True,
    )
    op.create_index(
        "ix_secret_vault_status_expiry",
        "secret_vault_entries",
        ["status", "expires_at"],
    )

    # 2. secret_rotation_policies
    op.create_table(
        "secret_rotation_policies",
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
            index=True,
        ),
        sa.Column(
            "secret_id",
            UUID(as_uuid=True),
            sa.ForeignKey("secret_vault_entries.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            unique=True,
        ),
        sa.Column(
            "rotation_interval_days",
            sa.Integer(),
            nullable=False,
            server_default="90",
        ),
        sa.Column(
            "auto_rotate", sa.Boolean(), nullable=False, server_default="true"
        ),
        sa.Column("last_rotation_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_rotation_due", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="ACTIVE",
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # 3. secret_access_policies
    op.create_table(
        "secret_access_policies",
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
            index=True,
        ),
        sa.Column(
            "secret_id",
            UUID(as_uuid=True),
            sa.ForeignKey("secret_vault_entries.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            unique=True,
        ),
        sa.Column(
            "min_role", sa.String(50), nullable=False, server_default="ADMIN"
        ),
        sa.Column(
            "require_approval",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column("allowed_ip_cidrs", JSON, nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Drop secret vault tables."""
    op.drop_table("secret_access_policies")
    op.drop_table("secret_rotation_policies")
    op.drop_table("secret_vault_entries")
