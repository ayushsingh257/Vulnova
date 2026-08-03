"""Domain entities and value objects for Phase 6.1 Celery & Distributed Isolated Worker Sandbox Cluster."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4


class WorkerStatus(str, Enum):
    """Lifecycle status of a Celery worker node in the cluster."""

    IDLE = "IDLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"
    PAUSED = "PAUSED"
    UNHEALTHY = "UNHEALTHY"


class WorkerTaskPriority(str, Enum):
    """Task priority queues for Celery job routing."""

    HIGH = "scans.high"
    DEFAULT = "scans.default"
    LOW = "scans.low"
    PRIORITY_AI = "ai.priority"


class WorkerTaskState(str, Enum):
    """Execution state of a distributed task."""

    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    CANCELLED = "CANCELLED"


@dataclass
class SandboxResourceLimits:
    """Resource caps and security constraints enforced on worker container sandboxes."""

    cpu_limit_vcpu: float = 1.0
    memory_limit_mb: int = 512
    disk_limit_mb: int = 1024
    max_processes: int = 100
    execution_timeout_sec: int = 3600
    run_as_uid: int = 10001
    run_as_gid: int = 10001
    read_only_rootfs: bool = True
    no_new_privs: bool = True
    dropped_capabilities: List[str] = field(default_factory=lambda: ["ALL"])
    network_egress_filtered: bool = True


@dataclass
class WorkerNode:
    """Domain model representing a registered Celery worker node in the cluster."""

    id: UUID = field(default_factory=uuid4)
    organization_id: UUID = field(default_factory=uuid4)
    worker_id: str = field(default_factory=lambda: f"worker-{uuid4().hex[:8]}")
    hostname: str = "localhost"
    status: WorkerStatus = WorkerStatus.IDLE
    current_task_count: int = 0
    max_concurrency: int = 4
    memory_usage_mb: float = 0.0
    cpu_percent: float = 0.0
    queue_subscriptions: List[str] = field(default_factory=lambda: ["scans.default"])
    sandbox_limits: SandboxResourceLimits = field(default_factory=SandboxResourceLimits)
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class WorkerTaskExecution:
    """Domain model representing an audit record of a distributed task execution."""

    id: UUID = field(default_factory=uuid4)
    task_id: str = field(default_factory=lambda: f"task-{uuid4().hex[:12]}")
    scan_id: Optional[UUID] = None
    organization_id: UUID = field(default_factory=uuid4)
    requested_by: UUID = field(default_factory=uuid4)
    worker_node_id: Optional[UUID] = None
    priority: WorkerTaskPriority = WorkerTaskPriority.DEFAULT
    task_name: str = "execute_scan_job_task"
    state: WorkerTaskState = WorkerTaskState.PENDING
    retry_count: int = 0
    runtime_ms: int = 0
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
