"""Domain Entity: RefreshToken."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass
class RefreshToken:
    """RefreshToken Domain Entity.

    Represents a hashed long-lived refresh token associated with a token family.
    """

    user_id: UUID
    family_id: UUID
    token_hash: str
    expires_at: datetime
    is_revoked: bool = False
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
