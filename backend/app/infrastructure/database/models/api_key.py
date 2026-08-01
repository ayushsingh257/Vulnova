"""SQLAlchemy ORM Model: APIKey."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base

if TYPE_CHECKING:
    from app.infrastructure.database.models.organization import OrganizationModel
    from app.infrastructure.database.models.user import UserModel


class APIKeyModel(Base):
    """APIKey SQLAlchemy ORM Model.

    Represents a machine-to-machine integration token for an Organization.
    """

    __tablename__ = "api_keys"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(8), index=True, nullable=False)
    key_hash: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    scopes: Mapped[List[str]] = mapped_column(
        JSON, default=lambda: ["read", "write"], nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    organization: Mapped["OrganizationModel"] = relationship(
        "OrganizationModel", back_populates="api_keys"
    )
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="api_keys")
