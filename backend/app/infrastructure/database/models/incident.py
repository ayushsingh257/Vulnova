"""SQLAlchemy ORM Models: Incident Response, Timelines, Escalations, and Post-Incident Reviews."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base

if TYPE_CHECKING:
    from app.infrastructure.database.models.audit_log import AuditLogModel
    from app.infrastructure.database.models.organization import OrganizationModel
    from app.infrastructure.database.models.user import UserModel


class IncidentModel(Base):
    """Incident SQLAlchemy ORM Model.

    Represents a classified security incident with lifecycle tracking.
    """

    __tablename__ = "incidents"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(
        String(50), nullable=False, default="SEV-3", index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="DETECTED", index=True
    )
    lead_investigator_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    affected_services: Mapped[List[str]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    indicators_of_compromise: Mapped[List[str]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    details: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    contained_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    organization: Mapped["OrganizationModel"] = relationship(
        "OrganizationModel", foreign_keys=[organization_id]
    )
    lead_investigator: Mapped[Optional["UserModel"]] = relationship(
        "UserModel", foreign_keys=[lead_investigator_id]
    )
    timelines: Mapped[List["IncidentTimelineModel"]] = relationship(
        "IncidentTimelineModel",
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="IncidentTimelineModel.timestamp",
    )
    escalations: Mapped[List["EscalationEventModel"]] = relationship(
        "EscalationEventModel",
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="EscalationEventModel.triggered_at",
    )
    post_incident_review: Mapped[Optional["PostIncidentReviewModel"]] = relationship(
        "PostIncidentReviewModel",
        back_populates="incident",
        uselist=False,
        cascade="all, delete-orphan",
    )


class IncidentTimelineModel(Base):
    """Incident Timeline SQLAlchemy ORM Model.

    Represents sequential lifecycle milestones and containment actions during incident investigation.
    """

    __tablename__ = "incident_timelines"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    incident_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    actor_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    phase: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    audit_log_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("audit_logs.id", ondelete="SET NULL"),
        nullable=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
        nullable=False,
    )

    # Relationships
    incident: Mapped["IncidentModel"] = relationship(
        "IncidentModel", back_populates="timelines"
    )
    actor: Mapped[Optional["UserModel"]] = relationship(
        "UserModel", foreign_keys=[actor_id]
    )
    audit_log: Mapped[Optional["AuditLogModel"]] = relationship(
        "AuditLogModel", foreign_keys=[audit_log_id]
    )


class EscalationEventModel(Base):
    """Escalation Event SQLAlchemy ORM Model.

    Tracks notification dispatches, channels (PagerDuty, Slack, Email), and delivery status.
    """

    __tablename__ = "escalation_events"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    incident_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    triggered_by: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    channels: Mapped[List[str]] = mapped_column(JSONB, default=list, nullable=False)
    notification_status: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="DELIVERED")
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    details: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    # Relationships
    incident: Mapped["IncidentModel"] = relationship(
        "IncidentModel", back_populates="escalations"
    )
    user: Mapped[Optional["UserModel"]] = relationship(
        "UserModel", foreign_keys=[triggered_by]
    )


class PostIncidentReviewModel(Base):
    """Post-Incident Review (PIR) SQLAlchemy ORM Model.

    Stores comprehensive root cause analysis, timeline synthesis, and remediation action items.
    """

    __tablename__ = "post_incident_reviews"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    incident_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    author_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause: Mapped[str] = mapped_column(Text, nullable=False)
    impact_assessment: Mapped[str] = mapped_column(Text, nullable=False)
    timeline_summary: Mapped[str] = mapped_column(Text, nullable=False)
    lessons_learned: Mapped[List[str]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    action_items: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    incident: Mapped["IncidentModel"] = relationship(
        "IncidentModel", back_populates="post_incident_review"
    )
    author: Mapped[Optional["UserModel"]] = relationship(
        "UserModel", foreign_keys=[author_id]
    )
