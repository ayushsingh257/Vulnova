"""Organization Data Transfer Objects (DTOs) for Application Services and API Routers."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UpdateOrganizationRequest(BaseModel):
    """Payload for updating organization settings."""

    name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=255,
        description="Updated display name of the organization",
    )
    plan_tier: Optional[str] = Field(
        None,
        min_length=2,
        max_length=50,
        description="Updated subscription tier (e.g. ENTERPRISE_TRIAL, ENTERPRISE_PRO)",
    )


class OrganizationDetailResponse(BaseModel):
    """Detailed organization response model including active member count."""

    id: UUID
    name: str
    slug: str
    plan_tier: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    member_count: int

    model_config = ConfigDict(from_attributes=True)
