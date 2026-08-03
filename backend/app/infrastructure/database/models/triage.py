"""SQLAlchemy Models for Finding Triage History & Automated Suppression Rules."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class FindingTriageHistoryModel(Base):
    """SQLAlchemy model capturing immutable audit history of finding triage actions."""

    __tablename__ = "finding_triage_history"

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
    actor_user_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    previous_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="UNREVIEWED"
    )
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_accepted_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    organization = relationship("OrganizationModel", backref="triage_histories")
    finding = relationship("SecurityFindingModel", backref="triage_histories")
    actor_user = relationship("UserModel", backref="triage_actions")

    __table_args__ = (
        Index("idx_triage_history_org_finding", "organization_id", "finding_id"),
        Index("idx_triage_history_org_created", "organization_id", "created_at"),
    )


class FindingSuppressionRuleModel(Base):
    """SQLAlchemy model representing an automated false-positive finding suppression rule."""

    __tablename__ = "finding_suppression_rules"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by_user_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # EXACT_CWE, TARGET_PATTERN, PLUGIN_ID, COMPOSITE
    plugin_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cwe_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    target_pattern: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, index=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    organization = relationship("OrganizationModel", backref="suppression_rules")
    created_by_user = relationship("UserModel", backref="created_suppression_rules")

    __table_args__ = (
        Index("idx_suppression_rules_org_active", "organization_id", "is_active"),
    )
