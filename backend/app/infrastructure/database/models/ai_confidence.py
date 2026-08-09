"""SQLAlchemy ORM models for Phase 5.5 AI False Positive Filter & Finding Confidence Intelligence Engine."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base

if TYPE_CHECKING:
    from app.infrastructure.database.models.assessment import SecurityFindingModel


class AIFindingConfidenceAnalysisModel(Base):
    """Master ORM model representing an AI confidence assessment with score calibration metadata."""

    __tablename__ = "ai_finding_confidence_analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("security_findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    classification: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )  # 'TRUE_POSITIVE', 'FALSE_POSITIVE', 'NEEDS_REVIEW'
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_evidence: Mapped[str] = mapped_column(Text, nullable=False)
    contradicting_evidence: Mapped[str] = mapped_column(Text, nullable=False)
    missing_information: Mapped[str] = mapped_column(Text, nullable=False)
    validation_requirements: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    composite_risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_used: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="GENERATED", index=True
    )  # 'GENERATED', 'REVIEWED', 'ACCEPTED', 'REJECTED', 'STALE', 'FAILED'
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── AI Confidence Score Calibration Metadata ──
    predicted_confidence_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    analyst_final_decision: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True
    )  # 'ACCEPTED', 'REJECTED', 'TRUE_POSITIVE', 'FALSE_POSITIVE'
    confidence_accuracy_delta: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )
    feedback_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )

    # Relationships
    finding: Mapped["SecurityFindingModel"] = relationship(
        "SecurityFindingModel", backref="confidence_analyses"
    )
    similarity_matches: Mapped[List["AIFindingSimilarityMatchModel"]] = relationship(
        "AIFindingSimilarityMatchModel",
        backref="confidence_analysis",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_ai_conf_org_finding", "organization_id", "finding_id"),
        Index("idx_ai_conf_org_class", "organization_id", "classification"),
        Index("idx_ai_conf_org_created", "organization_id", "created_at"),
    )


class AIFindingSimilarityMatchModel(Base):
    """Detail ORM model representing duplicate or related finding similarity correlation."""

    __tablename__ = "ai_finding_similarity_matches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    confidence_analysis_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_finding_confidence_analyses.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    source_finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("security_findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    matched_finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("security_findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    similarity_reason: Mapped[str] = mapped_column(Text, nullable=False)
    matched_signals: Mapped[Optional[List[str]]] = mapped_column(
        JSONB, nullable=True
    )  # ['CVE', 'CWE', 'ENDPOINT', 'ASSET_NODE', 'PLUGIN_ID', 'VULNERABILITY_TITLE', 'AFFECTED_COMPONENT', 'ATTACK_TECHNIQUE']
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="GENERATED")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )

    __table_args__ = (
        Index("idx_ai_sim_org_source", "organization_id", "source_finding_id"),
        Index("idx_ai_sim_score", "similarity_score"),
    )


class FindingVerificationAttemptModel(Base):
    """ORM Model representing automated safe re-probe finding verification attempts."""

    __tablename__ = "finding_verification_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("security_findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    verification_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="UNVERIFIED", index=True
    )  # 'UNVERIFIED', 'VERIFYING', 'CONFIRMED', 'FALSE_POSITIVE', 'NEEDS_REVIEW'
    strategy: Mapped[str] = mapped_column(Text, nullable=False)
    probe_response_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    probe_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_reproduced: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )

    __table_args__ = (
        Index("idx_verify_attempt_org_finding", "organization_id", "finding_id"),
    )


class FindingReviewModel(Base):
    """ORM Model representing human security analyst decision review audits."""

    __tablename__ = "finding_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("security_findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    decision: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # 'CONFIRM', 'FALSE_POSITIVE', 'ACCEPT_RISK', 'REQUEST_MORE_EVIDENCE'
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_snapshot: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )

    __table_args__ = (
        Index("idx_finding_review_org_finding", "organization_id", "finding_id"),
    )


class RemediationApprovalHistoryModel(Base):
    """ORM Model auditing human-in-the-loop remediation recommendation approvals."""

    __tablename__ = "remediation_approval_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    remediation_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_remediation_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    finding_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("security_findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    previous_state: Mapped[str] = mapped_column(String(50), nullable=False)
    new_state: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # 'AI_RECOMMENDED', 'ANALYST_REVIEW', 'APPROVED_FOR_IMPLEMENTATION', 'IMPLEMENTED', 'VERIFIED'
    action_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True
    )

    __table_args__ = (
        Index(
            "idx_remediation_approval_org_plan",
            "organization_id",
            "remediation_plan_id",
        ),
    )
