"""Domain Entity: User."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class User:
    """User Domain Entity.

    Represents an authenticated user associated with an Organization tenant.
    """

    organization_id: UUID
    email: str
    password_hash: str
    full_name: str
    role: str = "SECURITY_ANALYST"
    is_active: bool = True
    is_mfa_enabled: bool = False
    mfa_secret: Optional[str] = None
    last_login_at: Optional[datetime] = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
