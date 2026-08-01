"""Domain Entity: AuditLog."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


@dataclass
class AuditLog:
    """AuditLog Domain Entity.

    Represents an immutable security audit trail event for an Organization.
    """

    organization_id: UUID
    action: str
    resource_type: str
    actor_user_id: Optional[UUID] = None
    resource_id: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
