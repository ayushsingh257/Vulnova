"""SQLAlchemy ORM Model for Risk Posture Snapshots."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class RiskPostureSnapshotModel(Base):
    """SQLAlchemy model storing daily historical security risk snapshots per organization."""

    __tablename__ = "risk_posture_snapshots"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    composite_risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    posture_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="SECURE"
    )
    total_targets_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_open_findings: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    critical_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    high_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    medium_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    low_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    info_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    mttr_hours: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    snapshot_date: Mapped[date] = mapped_column(
        Date, nullable=False, default=func.current_date(), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    organization = relationship("OrganizationModel", backref="risk_posture_snapshots")

    __table_args__ = (
        Index(
            "idx_risk_snapshots_org_date",
            "organization_id",
            "snapshot_date",
            unique=True,
        ),
    )
