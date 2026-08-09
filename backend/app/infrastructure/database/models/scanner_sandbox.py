"""SQLAlchemy ORM Model for Ephemeral Scanner Execution Sandboxes."""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class ScannerSandboxModel(Base):
    """SQLAlchemy model representing an ephemeral container sandbox for scan isolation."""

    __tablename__ = "scanner_sandboxes"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scan_job_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("assessment_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    container_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    image_name: Mapped[str] = mapped_column(
        String(255), nullable=False, default="vulnova-scanner-sandbox:v1.0.0"
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="CREATED", index=True
    )
    cpu_limit: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0")
    memory_limit: Mapped[str] = mapped_column(
        String(50), nullable=False, default="512m"
    )
    read_only_rootfs: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    network_mode: Mapped[str] = mapped_column(
        String(100), nullable=False, default="vulnova_sandbox_net"
    )
    exit_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    execution_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    destroyed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_scanner_sandboxes_org_status", "organization_id", "status"),
        Index("ix_scanner_sandboxes_job_status", "scan_job_id", "status"),
    )
