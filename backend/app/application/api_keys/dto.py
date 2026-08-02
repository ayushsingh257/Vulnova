"""API Key Data Transfer Objects (DTOs) for Application Services and Routers."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CreateAPIKeyRequest(BaseModel):
    """Payload for creating a new machine-to-machine API key."""

    name: str = Field(
        min_length=2,
        max_length=255,
        description="Descriptive label for the API key",
    )
    scopes: List[str] = Field(
        default_factory=lambda: ["read", "write"],
        description="Assigned permission scopes for the key",
    )
    expires_in_days: Optional[int] = Field(
        None,
        ge=1,
        le=365,
        description="Optional duration in days until key expiration (1-365 days)",
    )


class APIKeyCreateResponse(BaseModel):
    """Response payload returned ONLY ONCE upon API key creation containing raw_key."""

    id: UUID
    organization_id: UUID
    user_id: UUID
    name: str
    key_prefix: str
    raw_key: str = Field(
        description="Plain-text API key returned ONLY ONCE. Unrecoverable after creation.",
    )
    scopes: List[str]
    expires_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class APIKeyResponse(BaseModel):
    """Public metadata response model for an API key (never contains raw secret or hash)."""

    id: UUID
    organization_id: UUID
    user_id: UUID
    name: str
    key_prefix: str
    scopes: List[str]
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class APIKeyListResponse(BaseModel):
    """Response list wrapper for organization API keys."""

    api_keys: List[APIKeyResponse]
    total: int
