"""SQLAlchemy Models for Enterprise Secrets Vault & KMS Credential Governance (Phase 12.8)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base

# Universal JSON type mapping (supports PostgreSQL JSONB and SQLite JSON fallback)
JSONType = JSONB().with_variant(Text, "sqlite")


class SecretVaultEntryModel(Base):
    """Stores envelope-encrypted enterprise secrets, encrypted DEKs, and KMS key metadata."""

    __tablename__ = "secret_vault_entries"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    secret_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    secret_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="GENERIC"
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="local")
    kek_id: Mapped[str] = mapped_column(String(255), nullable=False)
    encrypted_dek_hex: Mapped[str] = mapped_column(Text, nullable=False)
    encrypted_payload_hex: Mapped[str] = mapped_column(Text, nullable=False)
    nonce_hex: Mapped[str] = mapped_column(String(64), nullable=False)
    tag_hex: Mapped[str] = mapped_column(String(64), nullable=False)
    key_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="ACTIVE", index=True
    )
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONType, nullable=False, default=dict
    )
    last_rotated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    rotation_policy: Mapped[Optional["SecretRotationPolicyModel"]] = relationship(
        "SecretRotationPolicyModel",
        back_populates="secret_entry",
        uselist=False,
        cascade="all, delete-orphan",
    )
    access_policy: Mapped[Optional["SecretAccessPolicyModel"]] = relationship(
        "SecretAccessPolicyModel",
        back_populates="secret_entry",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "ix_secret_vault_org_name",
            "organization_id",
            "secret_name",
            unique=True,
        ),
        Index("ix_secret_vault_status_expiry", "status", "expires_at"),
    )


class SecretRotationPolicyModel(Base):
    """Defines automated key rotation intervals, deadlines, and execution states."""

    __tablename__ = "secret_rotation_policies"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    secret_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("secret_vault_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )
    rotation_interval_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=90
    )
    auto_rotate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_rotation_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    next_rotation_due: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="ACTIVE", index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    secret_entry: Mapped["SecretVaultEntryModel"] = relationship(
        "SecretVaultEntryModel", back_populates="rotation_policy"
    )


class SecretAccessPolicyModel(Base):
    """Enforces least-privilege role boundaries and IP access restrictions on sensitive secrets."""

    __tablename__ = "secret_access_policies"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4, nullable=False
    )
    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    secret_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("secret_vault_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )
    min_role: Mapped[str] = mapped_column(String(50), nullable=False, default="ADMIN")
    require_approval: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    allowed_ip_cidrs: Mapped[List[str]] = mapped_column(
        JSONType, nullable=False, default=list
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    secret_entry: Mapped["SecretVaultEntryModel"] = relationship(
        "SecretVaultEntryModel", back_populates="access_policy"
    )
