"""SQLAlchemy Models for AI Finding Explanations & Impact Analysis Reports."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
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


class AIFindingExplanationModel(Base):
    """SQLAlchemy model for AI-generated finding explanations (immutable append-only history)."""

    __tablename__ = "ai_finding_explanations"

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
    vulnerability_summary: Mapped[str] = mapped_column(Text, nullable=False)
    technical_root_cause: Mapped[str] = mapped_column(Text, nullable=False)
    affected_asset_context: Mapped[str] = mapped_column(Text, nullable=False)
    exploitability_analysis: Mapped[str] = mapped_column(Text, nullable=False)
    business_impact: Mapped[str] = mapped_column(Text, nullable=False)
    attack_prerequisites: Mapped[str] = mapped_column(Text, nullable=False)
    severity_reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    remediation_priority: Mapped[str] = mapped_column(Text, nullable=False)

    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_used: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="COMPLETED", index=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    organization = relationship("OrganizationModel", backref="ai_explanations")
    finding = relationship("SecurityFindingModel", backref="ai_explanations")

    __table_args__ = (
        Index("idx_ai_explanations_org_finding", "organization_id", "finding_id"),
        Index("idx_ai_explanations_org_created", "organization_id", "created_at"),
    )


class AIImpactAnalysisModel(Base):
    """SQLAlchemy model for AI-generated impact analysis reports (immutable append-only history)."""

    __tablename__ = "ai_impact_analyses"

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
    technical_impact_summary: Mapped[str] = mapped_column(Text, nullable=False)
    executive_impact_summary: Mapped[str] = mapped_column(Text, nullable=False)
    risk_justification: Mapped[str] = mapped_column(Text, nullable=False)
    affected_business_components: Mapped[str] = mapped_column(Text, nullable=False)
    cvss_interpretation: Mapped[str] = mapped_column(Text, nullable=False)
    epss_context: Mapped[str] = mapped_column(Text, nullable=False)
    exposure_assessment: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_correlation: Mapped[str] = mapped_column(Text, nullable=False)

    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_used: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="COMPLETED", index=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    organization = relationship("OrganizationModel", backref="ai_impact_analyses")
    finding = relationship("SecurityFindingModel", backref="ai_impact_analyses")

    __table_args__ = (
        Index("idx_ai_impact_org_finding", "organization_id", "finding_id"),
        Index("idx_ai_impact_org_created", "organization_id", "created_at"),
    )
