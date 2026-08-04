"""Domain entities and value objects for Phase 6.5 Distributed Scan Scheduler & Recurrence Engine."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4


class RecurrenceFrequency(str, Enum):
    """Supported recurrence intervals for automated vulnerability assessments."""

    HOURLY = "HOURLY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    CUSTOM_CRON = "CUSTOM_CRON"


class ScheduleStatus(str, Enum):
    """Lifecycle state of an automated scan schedule."""

    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    EXPIRED = "EXPIRED"
    DISABLED = "DISABLED"


@dataclass
class ScanSchedule:
    """Domain model representing a recurring vulnerability assessment schedule."""

    id: UUID = field(default_factory=uuid4)
    organization_id: UUID = field(default_factory=uuid4)
    scan_target_id: UUID = field(default_factory=uuid4)
    name: str = ""
    cron_expression: str = "0 0 * * *"
    frequency: RecurrenceFrequency = RecurrenceFrequency.DAILY
    status: ScheduleStatus = ScheduleStatus.ACTIVE
    profile_id: str = "full_assessment"
    enabled_plugins: Optional[List[str]] = None
    total_runs_count: int = 0
    next_run_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_run_at: Optional[datetime] = None
    created_by: Optional[UUID] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class WorkerAutoscaleMetrics:
    """Value object capturing worker cluster capacity and autoscaling governance recommendations."""

    active_workers_count: int = 0
    idle_workers_count: int = 0
    pending_queue_depth: int = 0
    recommended_workers_count: int = 1
    scaling_action_suggested: str = "STABLE"  # "SCALE_UP" | "SCALE_DOWN" | "STABLE"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
