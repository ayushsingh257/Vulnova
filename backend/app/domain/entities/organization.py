"""Domain Entity: Organization (Tenant)."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass
class Organization:
    """Organization (Tenant) Domain Entity.

    Represents an isolated multi-tenant organization boundary.
    """

    name: str
    slug: str
    plan_tier: str = "ENTERPRISE_TRIAL"
    is_active: bool = True
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
