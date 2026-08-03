"""Domain entities and value objects for Phase 6.3 Scan Execution Lifecycle State Machine & Retry Engine."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class ScanExecutionState(str, Enum):
    """Granular execution states of a security assessment scan job."""

    QUEUED = "QUEUED"
    CRAWLING = "CRAWLING"
    ASSESSING = "ASSESSING"
    AI_ANALYSIS = "AI_ANALYSIS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    RETRYING = "RETRYING"


class ScanStateTransitionEvent(str, Enum):
    """Events triggering state machine transitions."""

    DISPATCH = "DISPATCH"
    START_CRAWL = "START_CRAWL"
    START_ASSESSMENT = "START_ASSESSMENT"
    START_AI_ANALYSIS = "START_AI_ANALYSIS"
    COMPLETE = "COMPLETE"
    FAIL = "FAIL"
    CANCEL = "CANCEL"
    RETRY = "RETRY"


@dataclass
class RetryPolicy:
    """Configurable backoff policy strategy for transient execution failures."""

    max_retries: int = 3
    base_delay_seconds: float = 5.0
    backoff_factor: float = 2.0
    max_delay_seconds: float = 300.0

    def compute_backoff_delay(self, retry_count: int) -> float:
        """Compute exponential backoff delay in seconds for current retry attempt."""
        delay = self.base_delay_seconds * (self.backoff_factor**retry_count)
        return min(delay, self.max_delay_seconds)


@dataclass
class ScanLockMetadata:
    """Value object representing an active distributed scan lock."""

    lock_key: str = ""
    organization_id: UUID = field(default_factory=uuid4)
    target_url: str = ""
    acquired_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ttl_seconds: int = 3600
    owner_id: str = ""
