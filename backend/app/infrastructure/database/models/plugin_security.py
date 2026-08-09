"""SQLAlchemy database models for Phase 12.7 Plugin Security Architecture.

Enforces cryptographic trust verification, manifest capability bounds, and out-of-process isolation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class PluginTrustedPublisherModel(Base):
    """SQLAlchemy model representing a verified and trusted plugin publisher."""

    __tablename__ = "plugin_trusted_publishers"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    publisher_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    publisher_name: Mapped[str] = mapped_column(String(255), nullable=False)
    public_key_hex: Mapped[str] = mapped_column(String(128), nullable=False)
    public_key_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    trust_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="TRUSTED", index=True
    )
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revocation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    organization = relationship(
        "OrganizationModel", backref="plugin_trusted_publishers"
    )

    __table_args__ = (
        Index("idx_plugin_pub_org_pub", "organization_id", "publisher_id"),
        Index(
            "idx_plugin_pub_fingerprint", "organization_id", "public_key_fingerprint"
        ),
    )


class PluginManifestModel(Base):
    """SQLAlchemy model storing registered plugin capability manifests."""

    __tablename__ = "plugin_manifests"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plugin_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    publisher_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    entrypoint: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    capabilities_json: Mapped[List[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    package_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    min_platform_version: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    organization = relationship("OrganizationModel", backref="plugin_manifests")

    __table_args__ = (
        Index("idx_plugin_manifest_org_plugin", "organization_id", "plugin_id"),
    )


class PluginSignatureModel(Base):
    """SQLAlchemy model recording cryptographic signature verification records for plugins."""

    __tablename__ = "plugin_signatures"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plugin_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    publisher_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    signature_hex: Mapped[str] = mapped_column(Text, nullable=False)
    public_key_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    verification_status: Mapped[str] = mapped_column(
        String(40), nullable=False, default="VERIFIED", index=True
    )
    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    details_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    organization = relationship("OrganizationModel", backref="plugin_signatures")

    __table_args__ = (
        Index("idx_plugin_sig_org_plugin", "organization_id", "plugin_id"),
    )


class PluginExecutionAuditModel(Base):
    """SQLAlchemy model tracking sandbox execution audits and capability governance for plugins."""

    __tablename__ = "plugin_execution_audits"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plugin_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    execution_status: Mapped[str] = mapped_column(
        String(40), nullable=False, index=True
    )
    sandbox_type: Mapped[str] = mapped_column(
        String(40), nullable=False, default="subprocess"
    )
    capabilities_granted: Mapped[List[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    exit_code: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actor_user_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    organization = relationship("OrganizationModel", backref="plugin_execution_audits")

    __table_args__ = (
        Index("idx_plugin_exec_org_plugin", "organization_id", "plugin_id"),
        Index("idx_plugin_exec_org_status", "organization_id", "execution_status"),
    )
