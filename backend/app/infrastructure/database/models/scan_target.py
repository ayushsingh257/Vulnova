"""SQLAlchemy ORM Models for Phase 6.2 Target Scan Configuration & Authorized Assessment Contract."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class ScanTargetModel(Base):
    """ORM Model for registered scan targets with multi-tenant isolation and ownership verification.

    Maps to the ``scan_targets`` table defined in DATABASE.md.
    """

    __tablename__ = "scan_targets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_url: Mapped[str] = mapped_column(Text, nullable=False)
    environment: Mapped[str] = mapped_column(
        String(50), nullable=False, default="PRODUCTION"
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="ACTIVE", index=True
    )
    is_ownership_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    ownership_verification_token: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
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

    organization = relationship("OrganizationModel", backref="scan_targets")

    __table_args__ = (
        Index("ix_scan_targets_org_url", "organization_id", "target_url"),
        Index("ix_scan_targets_org_status", "organization_id", "status"),
    )


class AuthorizationDeclarationModel(Base):
    """ORM Model for immutable authorization consent declarations.

    Records every legal authorization event for compliance audit trail.
    Each scan execution requires a valid authorization declaration linked to a registered scan target.
    """

    __tablename__ = "authorization_declarations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scan_target_id: Mapped[UUID] = mapped_column(
        ForeignKey("scan_targets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    declared_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_authorized: Mapped[bool] = mapped_column(Boolean, nullable=False)
    authorization_scope: Mapped[str] = mapped_column(
        String(50), nullable=False, default="full"
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    scan_target = relationship("ScanTargetModel", backref="authorization_declarations")

    __table_args__ = (
        Index(
            "ix_auth_decl_org_target",
            "organization_id",
            "scan_target_id",
        ),
    )
