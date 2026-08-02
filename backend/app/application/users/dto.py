"""User Data Transfer Objects (DTOs) for Application Services and API Routers."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UpdateUserProfileRequest(BaseModel):
    """Payload for updating the authenticated user's own profile."""

    full_name: str = Field(
        min_length=2,
        max_length=255,
        description="Updated full name of the user",
    )


class InviteUserRequest(BaseModel):
    """Payload for inviting/creating a new team member in an organization."""

    email: EmailStr = Field(description="Email address of the invited user")
    full_name: str = Field(
        min_length=2,
        max_length=255,
        description="Full name of the invited user",
    )
    password: str = Field(
        min_length=8,
        description="Initial password for the invited user",
    )
    role: str = Field(
        default="SECURITY_ANALYST",
        description="Assigned organization role (VIEWER, SECURITY_ANALYST, ADMIN, OWNER)",
    )


class UpdateUserRoleRequest(BaseModel):
    """Payload for modifying a team member's role."""

    role: str = Field(
        description="New role to assign (VIEWER, SECURITY_ANALYST, ADMIN, OWNER)",
    )


class UpdateUserStatusRequest(BaseModel):
    """Payload for activating or deactivating a team member."""

    is_active: bool = Field(
        description="True to activate user, False to deactivate user",
    )


class UserDetailResponse(BaseModel):
    """Detailed user profile response model."""

    id: UUID
    organization_id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    is_mfa_enabled: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """Response list wrapper for organization users."""

    users: List[UserDetailResponse]
    total: int
