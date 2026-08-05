"""Auth DTO (Data Transfer Objects) for Application Services and API Routers."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Registration request payload."""

    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2, max_length=255)
    organization_name: str = Field(min_length=2, max_length=255)
    organization_slug: str = Field(min_length=2, max_length=255)


class LoginRequest(BaseModel):
    """Login request payload."""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Refresh token request payload (optional if passed via cookie)."""

    refresh_token: Optional[str] = None


class UserResponse(BaseModel):
    """Authenticated user profile response."""

    id: UUID
    organization_id: UUID
    organization_name: str
    organization_slug: str
    email: str
    full_name: str
    role: str
    is_active: bool
    is_mfa_enabled: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Token response payload returned on login/refresh."""

    access_token: str
    token_type: str = "bearer"
    user: Optional[UserResponse] = None
    mfa_required: bool = False
    mfa_login_token: Optional[str] = None
