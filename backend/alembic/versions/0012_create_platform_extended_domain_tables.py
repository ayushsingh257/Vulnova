"""Create platform extended domain tables for full schema coverage

Revision ID: 0012_create_platform_extended_domain_tables
Revises: 0011_create_evidence_malware_tables
Create Date: 2026-08-18 08:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0012_create_platform_extended_domain_tables"
down_revision: Union[str, None] = "0011_create_evidence_malware_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all extended platform domain tables with multi-tenant isolation and composite performance indexes."""

    # 1. Asset Nodes
    op.create_table(
        "asset_nodes",
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
        sa.Column("node_type", sa.String(50), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("value", sa.String(1024), nullable=False, index=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "organization_id",
            "node_type",
            "value",
            name="uq_asset_node_org_type_val",
        ),
    )
    op.create_index(
        "ix_asset_nodes_org_type",
        "asset_nodes",
        ["organization_id", "node_type"],
    )

    # 2. Asset Relationships
    op.create_table(
        "asset_relationships",
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
            "source_node_id",
            UUID(as_uuid=True),
            sa.ForeignKey("asset_nodes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "target_node_id",
            UUID(as_uuid=True),
            sa.ForeignKey("asset_nodes.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("relationship_type", sa.String(50), nullable=False, index=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "organization_id",
            "source_node_id",
            "target_node_id",
            "relationship_type",
            name="uq_asset_rel_org_src_tgt_type",
        ),
    )
    op.create_index(
        "ix_asset_rel_org_src",
        "asset_relationships",
        ["organization_id", "source_node_id"],
    )

    # 3. Scan Targets
    op.create_table(
        "scan_targets",
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
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("target_url", sa.Text(), nullable=False),
        sa.Column(
            "environment",
            sa.String(50),
            nullable=False,
            server_default="PRODUCTION",
        ),
        sa.Column(
            "status", sa.String(50), nullable=False, server_default="ACTIVE", index=True
        ),
        sa.Column(
            "is_ownership_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("ownership_verification_token", sa.String(255), nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_scan_targets_org_url", "scan_targets", ["organization_id", "target_url"]
    )
    op.create_index(
        "ix_scan_targets_org_status", "scan_targets", ["organization_id", "status"]
    )

    # 4. Authorization Declarations
    op.create_table(
        "authorization_declarations",
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
            "scan_target_id",
            UUID(as_uuid=True),
            sa.ForeignKey("scan_targets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "declared_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("is_authorized", sa.Boolean(), nullable=False),
        sa.Column(
            "authorization_scope",
            sa.String(50),
            nullable=False,
            server_default="full",
        ),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_auth_decl_org_target",
        "authorization_declarations",
        ["organization_id", "scan_target_id"],
    )

    # 5. Assessment Jobs
    op.create_table(
        "assessment_jobs",
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
        sa.Column("target_url", sa.String(1024), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, index=True),
        sa.Column(
            "profile_id",
            sa.String(50),
            nullable=False,
            server_default="full_assessment",
            index=True,
        ),
        sa.Column("policy_json", sa.JSON(), nullable=True),
        sa.Column("enabled_plugins_json", sa.JSON(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("error_message", sa.String(2048), nullable=True),
        sa.Column(
            "execution_state",
            sa.String(50),
            nullable=False,
            server_default="QUEUED",
            index=True,
        ),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_retries", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("current_step", sa.String(100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # 6. Security Findings
    op.create_table(
        "security_findings",
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
            "assessment_job_id",
            UUID(as_uuid=True),
            sa.ForeignKey("assessment_jobs.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "asset_node_id",
            UUID(as_uuid=True),
            sa.ForeignKey("asset_nodes.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("plugin_id", sa.String(100), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, index=True),
        sa.Column("category", sa.String(50), nullable=False, index=True),
        sa.Column("cve_id", sa.String(50), nullable=True),
        sa.Column("cwe_id", sa.String(50), nullable=True),
        sa.Column("remediation", sa.Text(), nullable=True),
        sa.Column("evidence_json", sa.JSON(), nullable=True),
        sa.Column("cvss_json", sa.JSON(), nullable=True),
        sa.Column("epss_json", sa.JSON(), nullable=True),
        sa.Column("risk_score", sa.Float(), nullable=True, index=True),
        sa.Column(
            "confidence",
            sa.String(20),
            nullable=True,
            server_default="HIGH",
            index=True,
        ),
        sa.Column(
            "is_duplicate",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "canonical_finding_id",
            UUID(as_uuid=True),
            sa.ForeignKey("security_findings.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("deduplication_hash", sa.String(64), nullable=True, index=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_security_findings_org_sev",
        "security_findings",
        ["organization_id", "severity"],
    )
    op.create_index(
        "ix_security_findings_org_cat",
        "security_findings",
        ["organization_id", "category"],
    )
    op.create_index(
        "ix_security_findings_org_risk",
        "security_findings",
        ["organization_id", "risk_score"],
    )

    # 7. Evidence Artifacts
    op.create_table(
        "evidence_artifacts",
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
        sa.Column("artifact_type", sa.String(50), nullable=False, index=True),
        sa.Column("storage_path", sa.String(1024), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_evidence_artifacts_org_finding",
        "evidence_artifacts",
        ["organization_id", "finding_id"],
    )

    # 8. Scan Schedules
    op.create_table(
        "scan_schedules",
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
            "scan_target_id",
            UUID(as_uuid=True),
            sa.ForeignKey("scan_targets.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("cron_expression", sa.String(100), nullable=False),
        sa.Column("frequency", sa.String(50), nullable=False, server_default="DAILY"),
        sa.Column(
            "status", sa.String(50), nullable=False, server_default="ACTIVE", index=True
        ),
        sa.Column(
            "profile_id",
            sa.String(100),
            nullable=False,
            server_default="full_assessment",
        ),
        sa.Column("enabled_plugins_json", sa.JSON(), nullable=True),
        sa.Column("total_runs_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "next_run_at",
            sa.DateTime(timezone=True),
            nullable=False,
            index=True,
        ),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_scan_schedules_org_status",
        "scan_schedules",
        ["organization_id", "status"],
    )
    op.create_index(
        "idx_scan_schedules_due_execution",
        "scan_schedules",
        ["status", "next_run_at"],
    )

    # 9. Worker Nodes
    op.create_table(
        "worker_nodes",
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
            "worker_id",
            sa.String(100),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column(
            "hostname", sa.String(255), nullable=False, server_default="localhost"
        ),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="IDLE", index=True
        ),
        sa.Column(
            "current_task_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("max_concurrency", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("memory_usage_mb", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("cpu_percent", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "queue_subscriptions",
            JSONB,
            nullable=False,
            server_default='["scans.default"]',
        ),
        sa.Column(
            "sandbox_limits",
            JSONB,
            nullable=False,
            server_default='{"cpu_limit_vcpu": 1.0, "memory_limit_mb": 512, "read_only_rootfs": true, "no_new_privs": true, "run_as_uid": 10001}',
        ),
        sa.Column(
            "last_heartbeat",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_worker_node_org_status",
        "worker_nodes",
        ["organization_id", "status"],
    )
    op.create_index(
        "idx_worker_node_heartbeat",
        "worker_nodes",
        ["last_heartbeat"],
    )

    # 10. Worker Task Executions
    op.create_table(
        "worker_task_executions",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("task_id", sa.String(100), nullable=False, unique=True, index=True),
        sa.Column(
            "scan_id",
            UUID(as_uuid=True),
            sa.ForeignKey("assessment_jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
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
            "worker_node_id",
            UUID(as_uuid=True),
            sa.ForeignKey("worker_nodes.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "priority",
            sa.String(50),
            nullable=False,
            server_default="scans.default",
        ),
        sa.Column("task_name", sa.String(255), nullable=False),
        sa.Column(
            "state",
            sa.String(20),
            nullable=False,
            server_default="PENDING",
            index=True,
        ),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("runtime_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_worker_task_org_state",
        "worker_task_executions",
        ["organization_id", "state"],
    )
    op.create_index(
        "idx_worker_task_scan",
        "worker_task_executions",
        ["scan_id"],
    )

    # 11. Finding Triage History
    op.create_table(
        "finding_triage_history",
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
            "actor_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "previous_status",
            sa.String(50),
            nullable=False,
            server_default="UNREVIEWED",
        ),
        sa.Column("new_status", sa.String(50), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("risk_accepted_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
    )
    op.create_index(
        "idx_triage_history_org_finding",
        "finding_triage_history",
        ["organization_id", "finding_id"],
    )
    op.create_index(
        "idx_triage_history_org_created",
        "finding_triage_history",
        ["organization_id", "created_at"],
    )

    # 12. Finding Suppression Rules
    op.create_table(
        "finding_suppression_rules",
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
            "created_by_user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("rule_type", sa.String(50), nullable=False),
        sa.Column("plugin_id", sa.String(100), nullable=True),
        sa.Column("cwe_id", sa.String(50), nullable=True),
        sa.Column("target_pattern", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            index=True,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_suppression_rules_org_active",
        "finding_suppression_rules",
        ["organization_id", "is_active"],
    )

    # 13. Asset Snapshots
    op.create_table(
        "asset_snapshots",
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
            "assessment_job_id",
            UUID(as_uuid=True),
            sa.ForeignKey("assessment_jobs.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("total_assets", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_findings", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "critical_findings", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("high_findings", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("medium_findings", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("low_findings", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("info_findings", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_risk_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("max_risk_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
    )
    op.create_index(
        "idx_asset_snapshots_org_created",
        "asset_snapshots",
        ["organization_id", "created_at"],
    )

    # 14. Asset Change Events
    op.create_table(
        "asset_change_events",
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
            "asset_node_id",
            UUID(as_uuid=True),
            sa.ForeignKey("asset_nodes.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "assessment_job_id",
            UUID(as_uuid=True),
            sa.ForeignKey("assessment_jobs.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("change_type", sa.String(50), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("details_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
    )
    op.create_index(
        "idx_change_events_org_created",
        "asset_change_events",
        ["organization_id", "created_at"],
    )
    op.create_index(
        "idx_change_events_org_type",
        "asset_change_events",
        ["organization_id", "change_type"],
    )

    # 15. Risk Posture Snapshots
    op.create_table(
        "risk_posture_snapshots",
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
        sa.Column("composite_risk_score", sa.Float(), nullable=False),
        sa.Column(
            "posture_status",
            sa.String(50),
            nullable=False,
            server_default="SECURE",
        ),
        sa.Column(
            "total_targets_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "total_open_findings",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("critical_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("high_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("medium_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("low_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("info_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mttr_hours", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column(
            "snapshot_date",
            sa.Date(),
            nullable=False,
            server_default=sa.func.current_date(),
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_risk_snapshots_org_date",
        "risk_posture_snapshots",
        ["organization_id", "snapshot_date"],
        unique=True,
    )

    # 16. LLM Providers
    op.create_table(
        "llm_providers",
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
        sa.Column("provider_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("api_endpoint", sa.Text(), nullable=True),
        sa.Column("encrypted_api_key", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="10"),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            index=True,
        ),
        sa.Column(
            "is_healthy",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            index=True,
        ),
        sa.Column(
            "consecutive_failures",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cooldown_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_llm_providers_org_active",
        "llm_providers",
        ["organization_id", "is_active", "priority"],
    )

    # 17. LLM Models
    op.create_table(
        "llm_models",
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
        sa.Column("provider_type", sa.String(50), nullable=False),
        sa.Column("model_alias", sa.String(100), nullable=False, index=True),
        sa.Column("model_name", sa.String(255), nullable=False),
        sa.Column(
            "context_window_tokens",
            sa.Integer(),
            nullable=False,
            server_default="128000",
        ),
        sa.Column(
            "max_output_tokens",
            sa.Integer(),
            nullable=False,
            server_default="4096",
        ),
        sa.Column(
            "input_cost_per_1k_tokens",
            sa.Numeric(10, 6),
            nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "output_cost_per_1k_tokens",
            sa.Numeric(10, 6),
            nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "is_default",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_llm_models_org_alias",
        "llm_models",
        ["organization_id", "model_alias"],
    )

    # 18. Prompt Templates
    op.create_table(
        "prompt_templates",
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
        sa.Column("category", sa.String(50), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("user_prompt_template", sa.Text(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_prompt_templates_org_cat",
        "prompt_templates",
        ["organization_id", "category", "is_active"],
    )

    # 19. LLM Request Logs
    op.create_table(
        "llm_request_logs",
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
        sa.Column("provider_type", sa.String(50), nullable=False),
        sa.Column("model_used", sa.String(100), nullable=False),
        sa.Column("prompt_category", sa.String(50), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "completion_tokens", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=False, server_default="0.0"),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
    )
    op.create_index(
        "idx_llm_logs_org_created",
        "llm_request_logs",
        ["organization_id", "created_at"],
    )

    # 20. AI Finding Explanations
    op.create_table(
        "ai_finding_explanations",
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
        sa.Column("vulnerability_summary", sa.Text(), nullable=False),
        sa.Column("technical_root_cause", sa.Text(), nullable=False),
        sa.Column("affected_asset_context", sa.Text(), nullable=False),
        sa.Column("exploitability_analysis", sa.Text(), nullable=False),
        sa.Column("business_impact", sa.Text(), nullable=False),
        sa.Column("attack_prerequisites", sa.Text(), nullable=False),
        sa.Column("severity_reasoning", sa.Text(), nullable=False),
        sa.Column("remediation_priority", sa.Text(), nullable=False),
        sa.Column("model_used", sa.String(100), nullable=False),
        sa.Column("provider_used", sa.String(50), nullable=False),
        sa.Column("prompt_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="COMPLETED",
            index=True,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
    )
    op.create_index(
        "idx_ai_explanations_org_finding",
        "ai_finding_explanations",
        ["organization_id", "finding_id"],
    )
    op.create_index(
        "idx_ai_explanations_org_created",
        "ai_finding_explanations",
        ["organization_id", "created_at"],
    )

    # 21. AI Impact Analyses
    op.create_table(
        "ai_impact_analyses",
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
        sa.Column("technical_impact_summary", sa.Text(), nullable=False),
        sa.Column("executive_impact_summary", sa.Text(), nullable=False),
        sa.Column("risk_justification", sa.Text(), nullable=False),
        sa.Column("affected_business_components", sa.Text(), nullable=False),
        sa.Column("cvss_interpretation", sa.Text(), nullable=False),
        sa.Column("epss_context", sa.Text(), nullable=False),
        sa.Column("exposure_assessment", sa.Text(), nullable=False),
        sa.Column("evidence_correlation", sa.Text(), nullable=False),
        sa.Column("model_used", sa.String(100), nullable=False),
        sa.Column("provider_used", sa.String(50), nullable=False),
        sa.Column("prompt_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="COMPLETED",
            index=True,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
    )
    op.create_index(
        "idx_ai_impact_org_finding",
        "ai_impact_analyses",
        ["organization_id", "finding_id"],
    )
    op.create_index(
        "idx_ai_impact_org_created",
        "ai_impact_analyses",
        ["organization_id", "created_at"],
    )

    # 22. AI Attack Paths
    op.create_table(
        "ai_attack_paths",
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
            "root_finding_id",
            UUID(as_uuid=True),
            sa.ForeignKey("security_findings.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "source_asset_id",
            UUID(as_uuid=True),
            sa.ForeignKey("asset_nodes.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "target_asset_id",
            UUID(as_uuid=True),
            sa.ForeignKey("asset_nodes.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("attack_summary", sa.Text(), nullable=False),
        sa.Column("composite_risk_score", sa.Float(), nullable=False),
        sa.Column(
            "confidence_score",
            sa.Float(),
            nullable=False,
            server_default="1.0",
        ),
        sa.Column("model_used", sa.String(100), nullable=False),
        sa.Column("provider_used", sa.String(50), nullable=False),
        sa.Column("prompt_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="GENERATED",
            index=True,
        ),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column(
            "reviewed_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
    )
    op.create_index(
        "idx_ai_paths_org_finding",
        "ai_attack_paths",
        ["organization_id", "root_finding_id"],
    )
    op.create_index(
        "idx_ai_paths_org_status",
        "ai_attack_paths",
        ["organization_id", "status"],
    )
    op.create_index(
        "idx_ai_paths_org_created",
        "ai_attack_paths",
        ["organization_id", "created_at"],
    )

    # 23. AI Attack Path Steps
    op.create_table(
        "ai_attack_path_steps",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "attack_path_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_attack_paths.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("step_type", sa.String(50), nullable=False, index=True),
        sa.Column(
            "asset_node_id",
            UUID(as_uuid=True),
            sa.ForeignKey("asset_nodes.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "finding_id",
            UUID(as_uuid=True),
            sa.ForeignKey("security_findings.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("mitre_tactic", sa.String(100), nullable=False),
        sa.Column("mitre_technique_id", sa.String(50), nullable=False, index=True),
        sa.Column("mitre_technique_name", sa.String(255), nullable=False),
        sa.Column("attacker_action", sa.Text(), nullable=False),
        sa.Column("required_privilege", sa.String(100), nullable=False),
        sa.Column("evidence_reference", sa.Text(), nullable=True),
        sa.Column(
            "confidence_score",
            sa.Float(),
            nullable=False,
            server_default="1.0",
        ),
    )
    op.create_index(
        "idx_ai_steps_path_seq",
        "ai_attack_path_steps",
        ["attack_path_id", "sequence_number"],
    )
    op.create_index(
        "idx_ai_steps_mitre",
        "ai_attack_path_steps",
        ["mitre_technique_id"],
    )

    # 24. AI Remediation Plans
    op.create_table(
        "ai_remediation_plans",
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
            "root_finding_id",
            UUID(as_uuid=True),
            sa.ForeignKey("security_findings.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "attack_path_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_attack_paths.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("cve_id", sa.String(50), nullable=True, index=True),
        sa.Column("cwe_id", sa.String(50), nullable=True, index=True),
        sa.Column("affected_version", sa.String(100), nullable=True),
        sa.Column("fixed_version", sa.String(100), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("technical_solution", sa.Text(), nullable=False),
        sa.Column("business_solution", sa.Text(), nullable=False),
        sa.Column("risk_reduction_explanation", sa.Text(), nullable=False),
        sa.Column("validation_strategy", sa.Text(), nullable=False),
        sa.Column("composite_risk_score", sa.Float(), nullable=False),
        sa.Column(
            "ai_confidence_score",
            sa.Float(),
            nullable=False,
            server_default="1.0",
        ),
        sa.Column(
            "effectiveness_confidence_score",
            sa.Float(),
            nullable=False,
            server_default="1.0",
        ),
        sa.Column(
            "requires_backup",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "requires_downtime",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "rollback_available",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("model_used", sa.String(100), nullable=False),
        sa.Column("provider_used", sa.String(50), nullable=False),
        sa.Column("prompt_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "status",
            sa.String(30),
            nullable=False,
            server_default="GENERATED",
            index=True,
        ),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column(
            "reviewed_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
    )
    op.create_index(
        "idx_ai_remed_org_finding",
        "ai_remediation_plans",
        ["organization_id", "root_finding_id"],
    )
    op.create_index(
        "idx_ai_remed_org_status",
        "ai_remediation_plans",
        ["organization_id", "status"],
    )
    op.create_index(
        "idx_ai_remed_org_created",
        "ai_remediation_plans",
        ["organization_id", "created_at"],
    )

    # 25. AI Remediation Steps
    op.create_table(
        "ai_remediation_steps",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "remediation_plan_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_remediation_plans.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("step_type", sa.String(50), nullable=False, index=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("affected_component", sa.String(255), nullable=False),
        sa.Column("recommended_action", sa.Text(), nullable=False),
        sa.Column("validation_command", sa.Text(), nullable=True),
        sa.Column("rollback_strategy", sa.Text(), nullable=True),
        sa.Column(
            "confidence_score",
            sa.Float(),
            nullable=False,
            server_default="1.0",
        ),
    )
    op.create_index(
        "idx_ai_remed_step_plan_seq",
        "ai_remediation_steps",
        ["remediation_plan_id", "sequence_number"],
    )

    # 26. AI Patch Suggestions
    op.create_table(
        "ai_patch_suggestions",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "remediation_plan_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_remediation_plans.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("language", sa.String(50), nullable=False, index=True),
        sa.Column("file_type", sa.String(50), nullable=False),
        sa.Column("target_file_path", sa.String(500), nullable=True),
        sa.Column("original_code_snippet", sa.Text(), nullable=False),
        sa.Column("proposed_patch_diff", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("security_impact_notes", sa.Text(), nullable=False),
        sa.Column(
            "confidence_score",
            sa.Float(),
            nullable=False,
            server_default="1.0",
        ),
    )
    op.create_index(
        "idx_ai_patch_plan_lang",
        "ai_patch_suggestions",
        ["remediation_plan_id", "language"],
    )

    # 27. Security Knowledge Documents
    op.create_table(
        "security_knowledge_documents",
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
            nullable=True,
            index=True,
        ),
        sa.Column("source_type", sa.String(50), nullable=False, index=True),
        sa.Column(
            "ingestion_source",
            sa.String(50),
            nullable=False,
            server_default="MANUAL_UPLOAD",
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("external_ref_id", sa.String(100), nullable=True, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.String(50), nullable=False, server_default="1.0"),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="PENDING",
            index=True,
        ),
        sa.Column(
            "chunk_size_tokens", sa.Integer(), nullable=False, server_default="512"
        ),
        sa.Column(
            "chunk_overlap_tokens",
            sa.Integer(),
            nullable=False,
            server_default="64",
        ),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "embedding_model",
            sa.String(100),
            nullable=False,
            server_default="text-embedding-3-small",
        ),
        sa.Column(
            "embedding_dimension",
            sa.Integer(),
            nullable=False,
            server_default="1536",
        ),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("source_author", sa.String(255), nullable=True),
        sa.Column("published_date", sa.String(50), nullable=True),
        sa.Column("last_updated_date", sa.String(50), nullable=True),
        sa.Column("metadata_json", JSONB, nullable=False, server_default="{}"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "reviewed_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_sec_doc_org_source",
        "security_knowledge_documents",
        ["organization_id", "source_type"],
    )
    op.create_index(
        "idx_sec_doc_org_status",
        "security_knowledge_documents",
        ["organization_id", "status"],
    )

    # 28. Security Knowledge Chunks
    op.create_table(
        "security_knowledge_chunks",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "document_id",
            UUID(as_uuid=True),
            sa.ForeignKey("security_knowledge_documents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "organization_id",
            UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("embedding", JSONB, nullable=True),
        sa.Column(
            "embedding_model",
            sa.String(100),
            nullable=False,
            server_default="text-embedding-3-small",
        ),
        sa.Column(
            "embedding_dimension",
            sa.Integer(),
            nullable=False,
            server_default="1536",
        ),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("source_author", sa.String(255), nullable=True),
        sa.Column("chunk_metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_sec_chunk_doc_index",
        "security_knowledge_chunks",
        ["document_id", "chunk_index"],
    )
    op.create_index(
        "idx_sec_chunk_org",
        "security_knowledge_chunks",
        ["organization_id"],
    )

    # 29. RAG Search Logs
    op.create_table(
        "rag_search_logs",
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
        sa.Column("query_text", sa.Text(), nullable=False),
        sa.Column("top_k", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("min_similarity", sa.Float(), nullable=False, server_default="0.70"),
        sa.Column("results_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("matched_chunk_ids", JSONB, nullable=False, server_default="[]"),
        sa.Column(
            "search_latency_ms", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("retrieval_quality_score", sa.Float(), nullable=True),
        sa.Column("average_similarity_score", sa.Float(), nullable=True),
        sa.Column("analyst_feedback", sa.Text(), nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_rag_log_org_created",
        "rag_search_logs",
        ["organization_id", "created_at"],
    )

    # 30. AI Copilot Sessions
    op.create_table(
        "ai_copilot_sessions",
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
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "title",
            sa.String(255),
            nullable=False,
            server_default="New Security Investigation",
        ),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="ACTIVE", index=True
        ),
        sa.Column(
            "focused_finding_id",
            UUID(as_uuid=True),
            sa.ForeignKey("security_findings.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "model_alias", sa.String(100), nullable=False, server_default="default"
        ),
        sa.Column("temperature", sa.Float(), nullable=False, server_default="0.2"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_copilot_session_org_user",
        "ai_copilot_sessions",
        ["organization_id", "user_id"],
    )

    # 31. AI Copilot Messages
    op.create_table(
        "ai_copilot_messages",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "session_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_copilot_sessions.id", ondelete="CASCADE"),
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
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "agent_type",
            sa.String(50),
            nullable=False,
            server_default="SECURITY_ANALYST",
        ),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("response_confidence_score", sa.Float(), nullable=True),
        sa.Column("sources_used", JSONB, nullable=False, server_default="[]"),
        sa.Column("knowledge_chunks_used", JSONB, nullable=False, server_default="[]"),
        sa.Column("tools_called", JSONB, nullable=False, server_default="[]"),
        sa.Column("reasoning_summary", sa.Text(), nullable=True),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column(
            "prompt_version", sa.String(50), nullable=False, server_default="1.0"
        ),
        sa.Column(
            "response_evaluation_metadata",
            JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_copilot_msg_session_role",
        "ai_copilot_messages",
        ["session_id", "role"],
    )

    # 32. AI Copilot Context Memories
    op.create_table(
        "ai_copilot_context_memories",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "session_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_copilot_sessions.id", ondelete="CASCADE"),
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
        sa.Column("memory_key", sa.String(100), nullable=False),
        sa.Column("memory_value_json", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "memory_type",
            sa.String(50),
            nullable=False,
            server_default="INVESTIGATION_STATE",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_copilot_mem_session_key",
        "ai_copilot_context_memories",
        ["session_id", "memory_key"],
    )

    # 33. AI Copilot Tool Executions
    op.create_table(
        "ai_copilot_tool_executions",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "session_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_copilot_sessions.id", ondelete="CASCADE"),
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
        sa.Column(
            "message_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_copilot_messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("input_params_json", JSONB, nullable=False, server_default="{}"),
        sa.Column("output_summary_json", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "execution_status",
            sa.String(20),
            nullable=False,
            server_default="SUCCESS",
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # 34. AI Copilot Feedback
    op.create_table(
        "ai_copilot_feedback",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "session_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_copilot_sessions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "message_id",
            UUID(as_uuid=True),
            sa.ForeignKey("ai_copilot_messages.id", ondelete="CASCADE"),
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
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column(
            "is_helpful",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("feedback_category", sa.String(100), nullable=True),
        sa.Column("feedback_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # 35. Finding Reviews
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
        sa.Column("decision", sa.String(50), nullable=False, index=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("evidence_snapshot", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
    )
    op.create_index(
        "idx_finding_review_org_finding",
        "finding_reviews",
        ["organization_id", "finding_id"],
    )

    # 36. Remediation Approval History
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
            "approver_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", sa.String(50), nullable=False, index=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
    )
    op.create_index(
        "idx_remed_approval_org_plan",
        "remediation_approval_history",
        ["organization_id", "remediation_plan_id"],
    )


def downgrade() -> None:
    """Drop platform extended domain tables in reverse dependency order."""
    op.drop_index(
        "idx_remed_approval_org_plan", table_name="remediation_approval_history"
    )
    op.drop_table("remediation_approval_history")

    op.drop_index("idx_finding_review_org_finding", table_name="finding_reviews")
    op.drop_table("finding_reviews")

    op.drop_table("ai_copilot_feedback")
    op.drop_table("ai_copilot_tool_executions")

    op.drop_index(
        "idx_copilot_mem_session_key", table_name="ai_copilot_context_memories"
    )
    op.drop_table("ai_copilot_context_memories")

    op.drop_index("idx_copilot_msg_session_role", table_name="ai_copilot_messages")
    op.drop_table("ai_copilot_messages")

    op.drop_index("idx_copilot_session_org_user", table_name="ai_copilot_sessions")
    op.drop_table("ai_copilot_sessions")

    op.drop_index("idx_rag_log_org_created", table_name="rag_search_logs")
    op.drop_table("rag_search_logs")

    op.drop_index("idx_sec_chunk_org", table_name="security_knowledge_chunks")
    op.drop_index("idx_sec_chunk_doc_index", table_name="security_knowledge_chunks")
    op.drop_table("security_knowledge_chunks")

    op.drop_index("idx_sec_doc_org_status", table_name="security_knowledge_documents")
    op.drop_index("idx_sec_doc_org_source", table_name="security_knowledge_documents")
    op.drop_table("security_knowledge_documents")

    op.drop_index("idx_ai_patch_plan_lang", table_name="ai_patch_suggestions")
    op.drop_table("ai_patch_suggestions")

    op.drop_index("idx_ai_remed_step_plan_seq", table_name="ai_remediation_steps")
    op.drop_table("ai_remediation_steps")

    op.drop_index("idx_ai_remed_org_created", table_name="ai_remediation_plans")
    op.drop_index("idx_ai_remed_org_status", table_name="ai_remediation_plans")
    op.drop_index("idx_ai_remed_org_finding", table_name="ai_remediation_plans")
    op.drop_table("ai_remediation_plans")

    op.drop_index("idx_ai_steps_mitre", table_name="ai_attack_path_steps")
    op.drop_index("idx_ai_steps_path_seq", table_name="ai_attack_path_steps")
    op.drop_table("ai_attack_path_steps")

    op.drop_index("idx_ai_paths_org_created", table_name="ai_attack_paths")
    op.drop_index("idx_ai_paths_org_status", table_name="ai_attack_paths")
    op.drop_index("idx_ai_paths_org_finding", table_name="ai_attack_paths")
    op.drop_table("ai_attack_paths")

    op.drop_index("idx_ai_impact_org_created", table_name="ai_impact_analyses")
    op.drop_index("idx_ai_impact_org_finding", table_name="ai_impact_analyses")
    op.drop_table("ai_impact_analyses")

    op.drop_index(
        "idx_ai_explanations_org_created", table_name="ai_finding_explanations"
    )
    op.drop_index(
        "idx_ai_explanations_org_finding", table_name="ai_finding_explanations"
    )
    op.drop_table("ai_finding_explanations")

    op.drop_index("idx_llm_logs_org_created", table_name="llm_request_logs")
    op.drop_table("llm_request_logs")

    op.drop_index("idx_prompt_templates_org_cat", table_name="prompt_templates")
    op.drop_table("prompt_templates")

    op.drop_index("idx_llm_models_org_alias", table_name="llm_models")
    op.drop_table("llm_models")

    op.drop_index("idx_llm_providers_org_active", table_name="llm_providers")
    op.drop_table("llm_providers")

    op.drop_index("idx_risk_snapshots_org_date", table_name="risk_posture_snapshots")
    op.drop_table("risk_posture_snapshots")

    op.drop_index("idx_change_events_org_type", table_name="asset_change_events")
    op.drop_index("idx_change_events_org_created", table_name="asset_change_events")
    op.drop_table("asset_change_events")

    op.drop_index("idx_asset_snapshots_org_created", table_name="asset_snapshots")
    op.drop_table("asset_snapshots")

    op.drop_index(
        "idx_suppression_rules_org_active", table_name="finding_suppression_rules"
    )
    op.drop_table("finding_suppression_rules")

    op.drop_index("idx_triage_history_org_created", table_name="finding_triage_history")
    op.drop_index("idx_triage_history_org_finding", table_name="finding_triage_history")
    op.drop_table("finding_triage_history")

    op.drop_index("idx_worker_task_scan", table_name="worker_task_executions")
    op.drop_index("idx_worker_task_org_state", table_name="worker_task_executions")
    op.drop_table("worker_task_executions")

    op.drop_index("idx_worker_node_heartbeat", table_name="worker_nodes")
    op.drop_index("idx_worker_node_org_status", table_name="worker_nodes")
    op.drop_table("worker_nodes")

    op.drop_index("idx_scan_schedules_due_execution", table_name="scan_schedules")
    op.drop_index("idx_scan_schedules_org_status", table_name="scan_schedules")
    op.drop_table("scan_schedules")

    op.drop_index("ix_evidence_artifacts_org_finding", table_name="evidence_artifacts")
    op.drop_table("evidence_artifacts")

    op.drop_index("ix_security_findings_org_risk", table_name="security_findings")
    op.drop_index("ix_security_findings_org_cat", table_name="security_findings")
    op.drop_index("ix_security_findings_org_sev", table_name="security_findings")
    op.drop_table("security_findings")

    op.drop_table("assessment_jobs")

    op.drop_index("ix_auth_decl_org_target", table_name="authorization_declarations")
    op.drop_table("authorization_declarations")

    op.drop_index("ix_scan_targets_org_status", table_name="scan_targets")
    op.drop_index("ix_scan_targets_org_url", table_name="scan_targets")
    op.drop_table("scan_targets")

    op.drop_index("ix_asset_rel_org_src", table_name="asset_relationships")
    op.drop_table("asset_relationships")

    op.drop_index("ix_asset_nodes_org_type", table_name="asset_nodes")
    op.drop_table("asset_nodes")
