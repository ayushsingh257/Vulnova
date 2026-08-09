"""SQLAlchemy ORM Model for Phase 12.5 Scan Approval Requests."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import TIMESTAMP, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class ScanApprovalRequestModel(Base):
    """ORM Model for sensitive asset scan approval workflows.

    Maps to the ``scan_approval_requests`` table.
    """

    __tablename__ = "scan_approval_requests"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scan_job_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("assessment_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_id: Mapped[UUID] = mapped_column(
        ForeignKey("scan_targets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requested_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    approved_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PENDING_APPROVAL", index=True
    )
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("idx_scan_approval_org_status", "organization_id", "status"),
        Index("idx_scan_approval_target_status", "target_id", "status"),
    )
