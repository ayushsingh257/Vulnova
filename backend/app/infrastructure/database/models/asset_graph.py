"""SQLAlchemy Database Models for Attack Surface Asset Graph & Relationships."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class AssetNodeModel(Base):
    """SQLAlchemy model representing an Attack Surface Asset Node."""

    __tablename__ = "asset_nodes"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    organization = relationship("OrganizationModel", backref="asset_nodes")

    __table_args__ = (
        UniqueConstraint(
            "organization_id", "node_type", "value", name="uq_asset_node_org_type_val"
        ),
        Index("ix_asset_nodes_org_type", "organization_id", "node_type"),
    )


class AssetRelationshipModel(Base):
    """SQLAlchemy model representing an Edge Relationship between Asset Nodes."""

    __tablename__ = "asset_relationships"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_node_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("asset_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_node_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("asset_nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    organization = relationship("OrganizationModel", backref="asset_relationships")
    source_node = relationship("AssetNodeModel", foreign_keys=[source_node_id])
    target_node = relationship("AssetNodeModel", foreign_keys=[target_node_id])

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "source_node_id",
            "target_node_id",
            "relationship_type",
            name="uq_asset_rel_org_src_tgt_type",
        ),
        Index("ix_asset_rel_org_src", "organization_id", "source_node_id"),
    )
