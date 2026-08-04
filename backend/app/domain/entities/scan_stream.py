"""Domain entities and value objects for real-time scan event streaming and WebSocket connections."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


class ScanEventType(str, Enum):
    """Supported real-time scan stream event types."""

    STATE_CHANGE = "STATE_CHANGE"
    PROGRESS_UPDATE = "PROGRESS_UPDATE"
    PLUGIN_STARTED = "PLUGIN_STARTED"
    PLUGIN_COMPLETED = "PLUGIN_COMPLETED"
    FINDING_DISCOVERED = "FINDING_DISCOVERED"
    ERROR_LOG = "ERROR_LOG"
    HEARTBEAT = "HEARTBEAT"


@dataclass
class ScanStreamEvent:
    """Domain event representing a single real-time scan execution update."""

    job_id: UUID
    organization_id: UUID
    event_type: ScanEventType
    payload: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: f"evt_{uuid4().hex[:12]}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Serialize event to a JSON-compatible dictionary."""
        return {
            "event_id": self.event_id,
            "job_id": str(self.job_id),
            "organization_id": str(self.organization_id),
            "event_type": self.event_type.value,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class WebSocketConnectionParams:
    """Value object holding authenticated WebSocket client connection context."""

    user_id: UUID
    organization_id: UUID
    scan_id: UUID
    client_ip: Optional[str] = None
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
