"""SQLAlchemy ORM Models for Assessment Jobs and Security Findings."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class AssessmentJobModel(Base):
    """SQLAlchemy model representing an execution run of an assessment scan."""

    __tablename__ = "assessment_jobs"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    profile_id: Mapped[str] = mapped_column(
        String(50), nullable=False, default="full_assessment", index=True
    )
    policy_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    enabled_plugins_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    organization = relationship("OrganizationModel", backref="assessment_jobs")


class SecurityFindingModel(Base):
    """SQLAlchemy model representing a vulnerability finding produced by a plugin."""

    __tablename__ = "security_findings"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assessment_job_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessment_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_node_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("asset_nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    plugin_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    cve_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cwe_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    remediation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Phase 4.5 Intelligence & Normalization Extensions
    cvss_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    epss_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    risk_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, index=True
    )
    confidence: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, default="HIGH", index=True
    )
    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    canonical_finding_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("security_findings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    deduplication_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, index=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    organization = relationship("OrganizationModel", backref="security_findings")
    assessment_job = relationship("AssessmentJobModel", backref="findings")

    __table_args__ = (
        Index("ix_security_findings_org_sev", "organization_id", "severity"),
        Index("ix_security_findings_org_cat", "organization_id", "category"),
        Index("ix_security_findings_org_risk", "organization_id", "risk_score"),
    )


class EvidenceArtifactModel(Base):
    """SQLAlchemy model representing a proof evidence artifact attached to a finding."""

    __tablename__ = "evidence_artifacts"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    finding_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("security_findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    finding = relationship("SecurityFindingModel", backref="artifacts")

    __table_args__ = (
        Index("ix_evidence_artifacts_org_finding", "organization_id", "finding_id"),
    )
