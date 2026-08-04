"""Pydantic v2 DTOs for Enterprise Administration & Control Plane Use Cases."""

from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class OrganizationAdminResponse(BaseModel):
    """Organization administration metadata response payload."""

    id: str
    name: str
    slug: str
    plan_tier: str = "ENTERPRISE"
    is_active: bool = True
    member_count: int = 1
    total_scans_count: int = 0
    total_findings_count: int = 0
    active_api_keys_count: int = 0
    created_at: str
    updated_at: str


class UpdateOrganizationAdminRequest(BaseModel):
    """Request payload for updating organization metadata."""

    name: Optional[str] = Field(None, min_length=2, max_length=255)
    plan_tier: Optional[str] = Field(
        None, description="Plan tier: FREE, PRO, ENTERPRISE"
    )


class UserAdminItemDTO(BaseModel):
    """User account item representation for admin user management table."""

    id: str
    email: str
    full_name: str
    role: str
    is_active: bool = True
    is_mfa_enabled: bool = False
    created_at: str


class UserAdminListResponse(BaseModel):
    """Response payload for listing organization team members."""

    total_count: int
    users: List[UserAdminItemDTO] = Field(default_factory=list)


class InviteUserAdminRequest(BaseModel):
    """Request payload for inviting a new team member."""

    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    role: str = Field(
        "SECURITY_ANALYST", description="Role: OWNER, ADMIN, SECURITY_ANALYST, VIEWER"
    )


class UpdateUserRoleAdminRequest(BaseModel):
    """Request payload for changing a team member's RBAC role."""

    role: str = Field(..., description="Role: OWNER, ADMIN, SECURITY_ANALYST, VIEWER")


class PermissionBoundaryDTO(BaseModel):
    """Permission boundary representation in role matrix."""

    permission_key: str
    description: str
    minimum_role: str


class RolePermissionBoundaryDTO(BaseModel):
    """Role definition with associated permission boundaries."""

    role_name: str
    role_level: int
    description: str
    granted_permissions: List[str] = Field(default_factory=list)


class RolePermissionMatrixResponse(BaseModel):
    """Response payload for role-permission matrix visualization."""

    roles: List[RolePermissionBoundaryDTO] = Field(default_factory=list)
    permissions: List[PermissionBoundaryDTO] = Field(default_factory=list)


class APIKeyAdminItemDTO(BaseModel):
    """Integration API Key representation DTO."""

    id: str
    name: str
    key_prefix: str
    scopes: List[str] = Field(default_factory=list)
    created_by_user_id: Optional[str] = None
    created_at: str
    expires_at: Optional[str] = None
    last_used_at: Optional[str] = None
    is_active: bool = True


class APIKeyAdminListResponse(BaseModel):
    """Response payload for listing active organization API keys."""

    total_count: int
    api_keys: List[APIKeyAdminItemDTO] = Field(default_factory=list)


class CreateAPIKeyAdminRequest(BaseModel):
    """Request payload for creating a new integration API key."""

    name: str = Field(..., min_length=2, max_length=100)
    scopes: List[str] = Field(default_factory=lambda: ["scans:read", "findings:read"])
    expires_in_days: Optional[int] = Field(None, ge=1, le=365)


class CreateAPIKeyAdminResponse(BaseModel):
    """Response payload returned ONCE during API key creation (contains raw secret key)."""

    id: str
    name: str
    raw_api_key: str = Field(..., description="Raw API key — shown ONLY ONCE")
    key_prefix: str
    scopes: List[str] = Field(default_factory=list)
    created_at: str
    expires_at: Optional[str] = None


class SecurityOverviewAdminResponse(BaseModel):
    """Security overview posture and MFA status visibility response payload."""

    organization_id: str
    total_users_count: int = 1
    mfa_enrolled_count: int = 0
    mfa_enforcement_status: str = "OPTIONAL"
    session_security_policy: str = "STRICT_JWT_DUAL_TOKEN"
    audit_logging_enabled: bool = True
    last_security_audit_at: str
