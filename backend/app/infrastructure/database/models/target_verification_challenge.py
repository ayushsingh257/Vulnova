"""SQLAlchemy ORM Model for Phase 12.5 Target Verification Challenges."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import TIMESTAMP, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class TargetVerificationChallengeModel(Base):
    """ORM Model for DNS TXT and HTTP well-known target ownership verification challenges.

    Maps to the ``target_verification_challenges`` table.
    """

    __tablename__ = "target_verification_challenges"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    target_id: Mapped[UUID] = mapped_column(
        ForeignKey("scan_targets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    challenge_token: Mapped[str] = mapped_column(String(255), nullable=False)
    verification_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="DNS_TXT"
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PENDING", index=True
    )
    verification_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )

    __table_args__ = (
        Index("idx_target_verify_challenge_token", "challenge_token"),
        Index("idx_target_verify_org_status", "organization_id", "status"),
    )
