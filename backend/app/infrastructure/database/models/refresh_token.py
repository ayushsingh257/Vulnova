"""SQLAlchemy ORM Model: RefreshToken."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base

if TYPE_CHECKING:
    from app.infrastructure.database.models.user import UserModel


class RefreshTokenModel(Base):
    """RefreshToken SQLAlchemy ORM Model.

    Represents a long-lived refresh token associated with a token family for rotation.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    family_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), index=True, nullable=False
    )
    token_hash: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="refresh_tokens"
    )
