"""SQLAlchemy Models for Attack Surface Posture Snapshots & Historical Change Events."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
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


class AssetSnapshotModel(Base):
    """SQLAlchemy model representing a point-in-time security posture snapshot for a tenant organization."""

    __tablename__ = "asset_snapshots"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assessment_job_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessment_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    total_assets: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_findings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    critical_findings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    high_findings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    medium_findings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    low_findings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    info_findings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Risk scores calculated from RiskIntelligenceEngine composite scores
    avg_risk_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    max_risk_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    organization = relationship("OrganizationModel", backref="asset_snapshots")
    assessment_job = relationship("AssessmentJobModel", backref="asset_snapshots")

    __table_args__ = (
        Index("idx_asset_snapshots_org_created", "organization_id", "created_at"),
    )


class AssetChangeEventModel(Base):
    """SQLAlchemy model representing a discrete security posture delta change event."""

    __tablename__ = "asset_change_events"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_node_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("asset_nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assessment_job_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessment_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    change_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # ASSET_ADDED, ASSET_REMOVED, TECH_UPDATED, FINDING_NEW, FINDING_RESOLVED, FINDING_REOPENED
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    organization = relationship("OrganizationModel", backref="asset_change_events")
    asset_node = relationship("AssetNodeModel", backref="asset_change_events")
    assessment_job = relationship("AssessmentJobModel", backref="asset_change_events")

    __table_args__ = (
        Index("idx_change_events_org_created", "organization_id", "created_at"),
        Index("idx_change_events_org_type", "organization_id", "change_type"),
    )
