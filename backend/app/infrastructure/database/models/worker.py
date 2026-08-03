"""SQLAlchemy ORM Models for Phase 6.1 Celery & Distributed Isolated Worker Sandbox Cluster."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    FLOAT,
    INTEGER,
    TEXT,
    TIMESTAMP,
    ForeignKey,
    Index,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class WorkerNodeModel(Base):
    """ORM Model for registered Celery worker cluster nodes with tenant context."""

    __tablename__ = "worker_nodes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    worker_id: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    hostname: Mapped[str] = mapped_column(
        String(255), nullable=False, default="localhost"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="IDLE", index=True
    )  # IDLE, BUSY, OFFLINE, PAUSED, UNHEALTHY
    current_task_count: Mapped[int] = mapped_column(INTEGER, nullable=False, default=0)
    max_concurrency: Mapped[int] = mapped_column(INTEGER, nullable=False, default=4)
    memory_usage_mb: Mapped[float] = mapped_column(FLOAT, nullable=False, default=0.0)
    cpu_percent: Mapped[float] = mapped_column(FLOAT, nullable=False, default=0.0)
    queue_subscriptions: Mapped[List[str]] = mapped_column(
        JSONB, nullable=False, default=lambda: ["scans.default"]
    )
    sandbox_limits: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=lambda: {
            "cpu_limit_vcpu": 1.0,
            "memory_limit_mb": 512,
            "read_only_rootfs": True,
            "no_new_privs": True,
            "run_as_uid": 10001,
        },
    )
    last_heartbeat: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    task_executions: Mapped[List["WorkerTaskModel"]] = relationship(
        "WorkerTaskModel", back_populates="worker_node", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_worker_node_org_status", "organization_id", "status"),
        Index("idx_worker_node_heartbeat", "last_heartbeat"),
    )


class WorkerTaskModel(Base):
    """ORM Model for auditing distributed task executions with multi-tenant isolation."""

    __tablename__ = "worker_task_executions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    task_id: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    scan_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("assessment_jobs.id", ondelete="SET NULL"), nullable=True
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requested_by: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    worker_node_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("worker_nodes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    priority: Mapped[str] = mapped_column(
        String(50), nullable=False, default="scans.default"
    )
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING", index=True
    )  # PENDING, STARTED, SUCCESS, FAILURE, RETRY, CANCELLED
    retry_count: Mapped[int] = mapped_column(INTEGER, nullable=False, default=0)
    runtime_ms: Mapped[int] = mapped_column(INTEGER, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(TEXT, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )

    # Relationships
    worker_node: Mapped[Optional[WorkerNodeModel]] = relationship(
        "WorkerNodeModel", back_populates="task_executions"
    )

    __table_args__ = (
        Index("idx_worker_task_org_state", "organization_id", "state"),
        Index("idx_worker_task_scan", "scan_id"),
    )
