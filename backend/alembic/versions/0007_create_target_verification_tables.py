"""Create target_verification_challenges and scan_approval_requests tables

Revision ID: 0007_create_target_verification_tables
Revises: 0006_create_scanner_sandbox_table
Create Date: 2026-08-09 08:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "0007_create_target_verification_tables"
down_revision: Union[str, None] = "0006_create_scanner_sandbox_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create target_verification_challenges and scan_approval_requests tables."""
    # 1. target_verification_challenges
    op.create_table(
        "target_verification_challenges",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "target_id",
            UUID(as_uuid=True),
            sa.ForeignKey("scan_targets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("challenge_token", sa.String(length=255), nullable=False),
        sa.Column(
            "verification_type",
            sa.String(length=50),
            nullable=False,
            server_default="DNS_TXT",
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="PENDING",
            index=True,
        ),
        sa.Column("verification_metadata", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("verified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_index(
        "idx_target_verify_challenge_token",
        "target_verification_challenges",
        ["challenge_token"],
    )
    op.create_index(
        "idx_target_verify_org_status",
        "target_verification_challenges",
        ["organization_id", "status"],
    )

    # 2. scan_approval_requests
    op.create_table(
        "scan_approval_requests",
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
            sa.ForeignKey("assessment_jobs.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "target_id",
            UUID(as_uuid=True),
            sa.ForeignKey("scan_targets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "requested_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "approved_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "status",
            sa.String(length=50),
            nullable=False,
            server_default="PENDING_APPROVAL",
            index=True,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_scan_approval_org_status",
        "scan_approval_requests",
        ["organization_id", "status"],
    )
    op.create_index(
        "idx_scan_approval_target_status",
        "scan_approval_requests",
        ["target_id", "status"],
    )


def downgrade() -> None:
    """Drop scan_approval_requests and target_verification_challenges tables."""
    op.drop_table("scan_approval_requests")
    op.drop_table("target_verification_challenges")
