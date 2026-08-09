"""Create finding_verification_attempts, finding_reviews, and remediation_approval_history tables

Revision ID: 0008_create_finding_confidence_and_remediation_tables
Revises: 0007_create_target_verification_tables
Create Date: 2026-08-09 09:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "0008_create_finding_confidence_and_remediation_tables"
down_revision: Union[str, None] = "0007_create_target_verification_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create finding verification, review, and remediation approval tables."""
    # 1. finding_verification_attempts
    op.create_table(
        "finding_verification_attempts",
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
            "finding_id",
            UUID(as_uuid=True),
            sa.ForeignKey("security_findings.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "verification_status",
            sa.String(length=50),
            nullable=False,
            server_default="UNVERIFIED",
            index=True,
        ),
        sa.Column("strategy", sa.Text(), nullable=False),
        sa.Column("probe_response_status", sa.Integer(), nullable=True),
        sa.Column("probe_output", sa.Text(), nullable=True),
        sa.Column("is_reproduced", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "idx_verify_attempt_org_finding",
        "finding_verification_attempts",
        ["organization_id", "finding_id"],
    )

    # 2. finding_reviews
    op.create_table(
        "finding_reviews",
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
            "finding_id",
            UUID(as_uuid=True),
            sa.ForeignKey("security_findings.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "reviewer_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("decision", sa.String(length=50), nullable=False, index=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("evidence_snapshot", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "idx_finding_review_org_finding",
        "finding_reviews",
        ["organization_id", "finding_id"],
    )

    # 3. remediation_approval_history
    op.create_table(
        "remediation_approval_history",
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
            "remediation_plan_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_remediation_plans.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "finding_id",
            UUID(as_uuid=True),
            sa.ForeignKey("security_findings.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("previous_state", sa.String(length=50), nullable=False),
        sa.Column("new_state", sa.String(length=50), nullable=False, index=True),
        sa.Column(
            "action_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )
    op.create_index(
        "idx_remediation_approval_org_plan",
        "remediation_approval_history",
        ["organization_id", "remediation_plan_id"],
    )


def downgrade() -> None:
    """Drop remediation_approval_history, finding_reviews, and finding_verification_attempts tables."""
    op.drop_table("remediation_approval_history")
    op.drop_table("finding_reviews")
    op.drop_table("finding_verification_attempts")
