"""SQLAlchemy Database Models for AI Attack Path Synthesis & Step Progression."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
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


class AIAttackPathModel(Base):
    """SQLAlchemy model representing an AI-synthesized attack path (Option A master table)."""

    __tablename__ = "ai_attack_paths"

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
    source_asset_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("asset_nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_asset_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("asset_nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    attack_summary: Mapped[str] = mapped_column(Text, nullable=False)
    composite_risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    provider_used: Mapped[str] = mapped_column(String(50), nullable=False)
    prompt_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="GENERATED", index=True
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

    organization = relationship("OrganizationModel", backref="ai_attack_paths")
    root_finding = relationship("SecurityFindingModel", backref="ai_attack_paths")
    reviewer = relationship("UserModel", backref="reviewed_attack_paths")
    steps: Mapped[List["AIAttackPathStepModel"]] = relationship(
        "AIAttackPathStepModel",
        back_populates="attack_path",
        cascade="all, delete-orphan",
        order_by="AIAttackPathStepModel.sequence_number",
    )

    __table_args__ = (
        Index("idx_ai_paths_org_finding", "organization_id", "root_finding_id"),
        Index("idx_ai_paths_org_status", "organization_id", "status"),
        Index("idx_ai_paths_org_created", "organization_id", "created_at"),
    )


class AIAttackPathStepModel(Base):
    """SQLAlchemy model representing an individual step within an attack path graph (Option A detail table)."""

    __tablename__ = "ai_attack_path_steps"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    attack_path_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("ai_attack_paths.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    step_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    asset_node_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("asset_nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    finding_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("security_findings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    mitre_tactic: Mapped[str] = mapped_column(String(100), nullable=False)
    mitre_technique_id: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    mitre_technique_name: Mapped[str] = mapped_column(String(255), nullable=False)
    attacker_action: Mapped[str] = mapped_column(Text, nullable=False)
    required_privilege: Mapped[str] = mapped_column(String(100), nullable=False)
    evidence_reference: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    attack_path = relationship("AIAttackPathModel", back_populates="steps")

    __table_args__ = (
        Index("idx_ai_steps_path_seq", "attack_path_id", "sequence_number"),
        Index("idx_ai_steps_mitre", "mitre_technique_id"),
    )
