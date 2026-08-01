"""Domain Entity: APIKey."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4


@dataclass
class APIKey:
    """APIKey Domain Entity.

    Represents a machine-to-machine integration token for an Organization.
    """

    organization_id: UUID
    user_id: UUID
    name: str
    key_prefix: str
    key_hash: str
    scopes: List[str] = field(default_factory=lambda: ["read", "write"])
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
