"""SQLAlchemy Database Models for AI Remediation Engine, Steps, and Non-Executable Patch Suggestions."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class AIRemediationPlanModel(Base):
    """SQLAlchemy model representing an AI-synthesized remediation plan (Master Table)."""

    __tablename__ = "ai_remediation_plans"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    root_finding_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("security_findings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attack_path_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ai_attack_paths.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    cve_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    cwe_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    affected_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    fixed_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    technical_solution: Mapped[str] = mapped_column(Text, nullable=False)
    business_solution: Mapped[str] = mapped_column(Text, nullable=False)
    risk_reduction_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    validation_strategy: Mapped[str] = mapped_column(Text, nullable=False)
    composite_risk_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Dual Confidence Metrics
    ai_confidence_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0
    )
    effectiveness_confidence_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=1.0
    )

    # Operational Risk Flags
    requires_backup: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    requires_downtime: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    rollback_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_used: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="GENERATED", index=True
    )

    # Analyst Review Metadata
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    organization = relationship("OrganizationModel", backref="ai_remediation_plans")
    root_finding = relationship("SecurityFindingModel", backref="ai_remediation_plans")
    attack_path = relationship("AIAttackPathModel", backref="ai_remediation_plans")
    reviewer = relationship("UserModel", backref="reviewed_remediation_plans")

    steps: Mapped[List["AIRemediationStepModel"]] = relationship(
        "AIRemediationStepModel",
        back_populates="remediation_plan",
        cascade="all, delete-orphan",
        order_by="AIRemediationStepModel.sequence_number",
    )
    patch_suggestions: Mapped[List["AIPatchSuggestionModel"]] = relationship(
        "AIPatchSuggestionModel",
        back_populates="remediation_plan",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_ai_remed_org_finding", "organization_id", "root_finding_id"),
        Index("idx_ai_remed_org_status", "organization_id", "status"),
        Index("idx_ai_remed_org_created", "organization_id", "created_at"),
    )


class AIRemediationStepModel(Base):
    """SQLAlchemy model representing an individual step within a remediation plan (Detail Table)."""

    __tablename__ = "ai_remediation_steps"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    remediation_plan_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ai_remediation_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    step_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    affected_component: Mapped[str] = mapped_column(String(255), nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, nullable=False)
    validation_command: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rollback_strategy: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    remediation_plan = relationship("AIRemediationPlanModel", back_populates="steps")

    __table_args__ = (
        Index("idx_ai_remed_step_plan_seq", "remediation_plan_id", "sequence_number"),
    )


class AIPatchSuggestionModel(Base):
    """SQLAlchemy model representing a non-executable code or config patch diff suggestion."""

    __tablename__ = "ai_patch_suggestions"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    remediation_plan_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ai_remediation_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    language: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    original_code_snippet: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_patch_diff: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    security_impact_notes: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    remediation_plan = relationship(
        "AIRemediationPlanModel", back_populates="patch_suggestions"
    )

    __table_args__ = (
        Index("idx_ai_patch_plan_lang", "remediation_plan_id", "language"),
    )
