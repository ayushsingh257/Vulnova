"""SQLAlchemy ORM Model: User."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base

if TYPE_CHECKING:
    from app.infrastructure.database.models.api_key import APIKeyModel
    from app.infrastructure.database.models.audit_log import AuditLogModel
    from app.infrastructure.database.models.organization import OrganizationModel
    from app.infrastructure.database.models.refresh_token import RefreshTokenModel


class UserModel(Base):
    """User SQLAlchemy ORM Model.

    Represents an authenticated user associated with an Organization tenant.
    """

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(50), default="SECURITY_ANALYST", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    mfa_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    mfa_backup_codes: Mapped[Optional[str]] = mapped_column(String(4096), nullable=True)
    mfa_last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    @property
    def is_mfa_enabled(self) -> bool:
        return self.mfa_enabled

    @is_mfa_enabled.setter
    def is_mfa_enabled(self, value: bool) -> None:
        self.mfa_enabled = value

    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
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
    organization: Mapped["OrganizationModel"] = relationship(
        "OrganizationModel", back_populates="users"
    )
    refresh_tokens: Mapped[List["RefreshTokenModel"]] = relationship(
        "RefreshTokenModel", back_populates="user", cascade="all, delete-orphan"
    )
    api_keys: Mapped[List["APIKeyModel"]] = relationship(
        "APIKeyModel", back_populates="user", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[List["AuditLogModel"]] = relationship(
        "AuditLogModel", back_populates="actor_user"
    )
