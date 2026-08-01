"""SQLAlchemy ORM Model: AuditLog."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base

if TYPE_CHECKING:
    from app.infrastructure.database.models.organization import OrganizationModel
    from app.infrastructure.database.models.user import UserModel


class AuditLogModel(Base):
    """AuditLog SQLAlchemy ORM Model.

    Represents an immutable security audit event in PostgreSQL.
    """

    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    actor_user_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    client_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True, nullable=False
    )

    # Relationships
    organization: Mapped["OrganizationModel"] = relationship(
        "OrganizationModel", back_populates="audit_logs"
    )
    actor_user: Mapped[Optional["UserModel"]] = relationship(
        "UserModel", back_populates="audit_logs"
    )
