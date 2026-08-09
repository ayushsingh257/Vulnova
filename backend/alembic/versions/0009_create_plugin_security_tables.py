"""Create plugin security tables: plugin_trusted_publishers, plugin_manifests, plugin_signatures, and plugin_execution_audits

Revision ID: 0009_create_plugin_security_tables
Revises: 0008_create_finding_confidence_and_remediation_tables
Create Date: 2026-08-09 15:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON, UUID

# revision identifiers, used by Alembic.
revision: str = "0009_create_plugin_security_tables"
down_revision: Union[str, None] = "0008_create_finding_confidence_and_remediation_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create plugin security tables for Phase 12.7."""
    # 1. plugin_trusted_publishers
    op.create_table(
        "plugin_trusted_publishers",
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
        sa.Column("publisher_id", sa.String(100), nullable=False, index=True),
        sa.Column("publisher_name", sa.String(255), nullable=False),
        sa.Column("public_key_hex", sa.String(128), nullable=False),
        sa.Column("public_key_fingerprint", sa.String(64), nullable=False, index=True),
        sa.Column("trust_status", sa.String(30), nullable=False, server_default="TRUSTED", index=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revocation_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_plugin_pub_org_pub", "plugin_trusted_publishers", ["organization_id", "publisher_id"])
    op.create_index("idx_plugin_pub_fingerprint", "plugin_trusted_publishers", ["organization_id", "public_key_fingerprint"])

    # 2. plugin_manifests
    op.create_table(
        "plugin_manifests",
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
        sa.Column("plugin_id", sa.String(100), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("publisher_id", sa.String(100), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("entrypoint", sa.String(255), nullable=False, server_default=""),
        sa.Column("capabilities_json", JSON, nullable=False, server_default="[]"),
        sa.Column("package_hash", sa.String(64), nullable=False),
        sa.Column("min_platform_version", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_plugin_manifest_org_plugin", "plugin_manifests", ["organization_id", "plugin_id"])

    # 3. plugin_signatures
    op.create_table(
        "plugin_signatures",
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
        sa.Column("plugin_id", sa.String(100), nullable=False, index=True),
        sa.Column("publisher_id", sa.String(100), nullable=False, index=True),
        sa.Column("signature_hex", sa.Text(), nullable=False),
        sa.Column("public_key_fingerprint", sa.String(64), nullable=False),
        sa.Column("verification_status", sa.String(40), nullable=False, server_default="VERIFIED", index=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("details_json", JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_plugin_sig_org_plugin", "plugin_signatures", ["organization_id", "plugin_id"])

    # 4. plugin_execution_audits
    op.create_table(
        "plugin_execution_audits",
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
        sa.Column("plugin_id", sa.String(100), nullable=False, index=True),
        sa.Column("execution_status", sa.String(40), nullable=False, index=True),
        sa.Column("sandbox_type", sa.String(40), nullable=False, server_default="subprocess"),
        sa.Column("capabilities_granted", JSON, nullable=False, server_default="[]"),
        sa.Column("duration_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("exit_code", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actor_user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_plugin_exec_org_plugin", "plugin_execution_audits", ["organization_id", "plugin_id"])
    op.create_index("idx_plugin_exec_org_status", "plugin_execution_audits", ["organization_id", "execution_status"])


def downgrade() -> None:
    """Drop plugin security tables."""
    op.drop_table("plugin_execution_audits")
    op.drop_table("plugin_signatures")
    op.drop_table("plugin_manifests")
    op.drop_table("plugin_trusted_publishers")
