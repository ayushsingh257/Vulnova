"""Create scanner_sandboxes table for ephemeral scan execution isolation

Revision ID: 0006_create_scanner_sandbox_table
Revises: 0005_create_incident_response_tables
Create Date: 2026-08-09 07:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = "0006_create_scanner_sandbox_table"
down_revision: Union[str, None] = "0005_create_incident_response_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create scanner_sandboxes table and performance composite indexes."""
    op.create_table(
        "scanner_sandboxes",
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
            "scan_job_id",
            UUID(as_uuid=True),
            sa.ForeignKey("assessment_jobs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("container_id", sa.String(length=255), nullable=False, index=True),
        sa.Column(
            "image_name",
            sa.String(length=255),
            nullable=False,
            server_default="vulnova-scanner-sandbox:v1.0.0",
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="CREATED",
            index=True,
        ),
        sa.Column("cpu_limit", sa.String(length=50), nullable=False, server_default="1.0"),
        sa.Column("memory_limit", sa.String(length=50), nullable=False, server_default="512m"),
        sa.Column("read_only_rootfs", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "network_mode",
            sa.String(length=100),
            nullable=False,
            server_default="vulnova_sandbox_net",
        ),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("execution_metadata", JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("destroyed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index(
        "ix_scanner_sandboxes_org_status",
        "scanner_sandboxes",
        ["organization_id", "status"],
    )
    op.create_index(
        "ix_scanner_sandboxes_job_status",
        "scanner_sandboxes",
        ["scan_job_id", "status"],
    )


def downgrade() -> None:
    """Drop scanner_sandboxes table and associated indexes."""
    op.drop_index("ix_scanner_sandboxes_job_status", table_name="scanner_sandboxes")
    op.drop_index("ix_scanner_sandboxes_org_status", table_name="scanner_sandboxes")
    op.drop_table("scanner_sandboxes")
