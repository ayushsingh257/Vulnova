"""SQLAlchemy ORM Model: Organization."""

from datetime import datetime
from typing import TYPE_CHECKING, List
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base

if TYPE_CHECKING:
    from app.infrastructure.database.models.api_key import APIKeyModel
    from app.infrastructure.database.models.audit_log import AuditLogModel
    from app.infrastructure.database.models.user import UserModel


class OrganizationModel(Base):
    """Organization (Tenant) SQLAlchemy ORM Model.

    Represents the primary multi-tenant boundary in PostgreSQL.
    """

    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    plan_tier: Mapped[str] = mapped_column(
        String(50), default="ENTERPRISE_TRIAL", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    users: Mapped[List["UserModel"]] = relationship(
        "UserModel", back_populates="organization", cascade="all, delete-orphan"
    )
    api_keys: Mapped[List["APIKeyModel"]] = relationship(
        "APIKeyModel", back_populates="organization", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["AuditLogModel"]] = relationship(
        "AuditLogModel", back_populates="organization", cascade="all, delete-orphan"
    )
