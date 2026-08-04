"""Enterprise Administration & Control Plane REST API Router."""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.rbac import require_permission
from app.application.admin.admin_service import AdminService
from app.application.admin.dto import (
    APIKeyAdminListResponse,
    CreateAPIKeyAdminRequest,
    CreateAPIKeyAdminResponse,
    InviteUserAdminRequest,
    OrganizationAdminResponse,
    RolePermissionMatrixResponse,
    SecurityOverviewAdminResponse,
    UpdateOrganizationAdminRequest,
    UpdateUserRoleAdminRequest,
    UserAdminItemDTO,
    UserAdminListResponse,
)
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

router = APIRouter(prefix="/admin", tags=["Enterprise Administration & Governance"])


# ── Organization Metadata ───────────────────────────────


@router.get(
    "/organization",
    response_model=OrganizationAdminResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Organization Administrative Profile",
    description="Returns organization settings, subscription metadata, and member metrics for the authenticated tenant.",
)
async def get_organization_profile(
    current_user: UserModel = Depends(get_current_user_or_api_key),
    _: None = Depends(require_permission("organization:read")),
    db: AsyncSession = Depends(get_async_session),
) -> OrganizationAdminResponse:
    """Retrieve organization admin details."""
    service = AdminService(db)
    return await service.get_organization_details(current_user.organization_id)


@router.patch(
    "/organization",
    response_model=OrganizationAdminResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Organization Metadata",
    description="Updates organization display name or plan tier metadata with audit logging.",
)
async def update_organization_profile(
    req: UpdateOrganizationAdminRequest,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    _: None = Depends(require_permission("organization:update")),
    db: AsyncSession = Depends(get_async_session),
) -> OrganizationAdminResponse:
    """Update organization admin profile."""
    service = AdminService(db)
    return await service.update_organization_profile(
        current_user.organization_id, req, current_user
    )


# ── Team User Governance ────────────────────────────────


@router.get(
    "/users",
    response_model=UserAdminListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Organization Team Members",
    description="Returns all team members, assigned RBAC roles, and account statuses for the organization.",
)
async def list_organization_users(
    current_user: UserModel = Depends(get_current_user_or_api_key),
    _: None = Depends(require_permission("users:read")),
    db: AsyncSession = Depends(get_async_session),
) -> UserAdminListResponse:
    """List team members."""
    service = AdminService(db)
    return await service.list_users(current_user.organization_id)


@router.post(
    "/users/invite",
    response_model=UserAdminItemDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Invite New Team Member",
    description="Creates and invites a new user account to the organization with assigned RBAC role.",
)
async def invite_team_member(
    req: InviteUserAdminRequest,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    _: None = Depends(require_permission("users:invite")),
    db: AsyncSession = Depends(get_async_session),
) -> UserAdminItemDTO:
    """Invite team member."""
    service = AdminService(db)
    return await service.invite_user(current_user.organization_id, req, current_user)


@router.patch(
    "/users/{user_id}/role",
    response_model=UserAdminItemDTO,
    status_code=status.HTTP_200_OK,
    summary="Update Team Member Role",
    description="Modifies a team member's RBAC role, enforcing sole organization OWNER demotion protection.",
)
async def update_team_member_role(
    user_id: UUID,
    req: UpdateUserRoleAdminRequest,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    _: None = Depends(require_permission("users:update_role")),
    db: AsyncSession = Depends(get_async_session),
) -> UserAdminItemDTO:
    """Update team member role."""
    service = AdminService(db)
    return await service.update_user_role(
        current_user.organization_id, user_id, req, current_user
    )


@router.delete(
    "/users/{user_id}",
    response_model=UserAdminItemDTO,
    status_code=status.HTTP_200_OK,
    summary="Deactivate Team Member Account",
    description="Deactivates a team member account, enforcing self-deactivation and sole OWNER protection.",
)
async def deactivate_team_member(
    user_id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    _: None = Depends(require_permission("users:remove")),
    db: AsyncSession = Depends(get_async_session),
) -> UserAdminItemDTO:
    """Deactivate team member."""
    service = AdminService(db)
    return await service.deactivate_user(
        current_user.organization_id, user_id, current_user
    )


# ── RBAC Role-Permission Matrix ─────────────────────────


@router.get(
    "/roles",
    response_model=RolePermissionMatrixResponse,
    status_code=status.HTTP_200_OK,
    summary="Get RBAC Role-Permission Matrix",
    description="Returns permission boundary matrix comparing OWNER, ADMIN, SECURITY_ANALYST, and VIEWER roles.",
)
async def get_role_permission_matrix(
    current_user: UserModel = Depends(get_current_user_or_api_key),
    _: None = Depends(require_permission("users:read")),
    db: AsyncSession = Depends(get_async_session),
) -> RolePermissionMatrixResponse:
    """Retrieve role permission matrix."""
    service = AdminService(db)
    return await service.get_role_permission_matrix()


# ── API Key Governance ─────────────────────────────────


@router.get(
    "/api-keys",
    response_model=APIKeyAdminListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Active Integration API Keys",
    description="Returns active machine-to-machine API keys, scopes, prefixes, and last usage timestamps.",
)
async def list_integration_api_keys(
    current_user: UserModel = Depends(get_current_user_or_api_key),
    _: None = Depends(require_permission("api_keys:read")),
    db: AsyncSession = Depends(get_async_session),
) -> APIKeyAdminListResponse:
    """List API keys."""
    service = AdminService(db)
    return await service.list_api_keys(current_user.organization_id)


@router.post(
    "/api-keys",
    response_model=CreateAPIKeyAdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Integration API Key",
    description="Generates a new machine-to-machine API key. The raw secret key is returned ONLY ONCE.",
)
async def generate_integration_api_key(
    req: CreateAPIKeyAdminRequest,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    _: None = Depends(require_permission("api_keys:create")),
    db: AsyncSession = Depends(get_async_session),
) -> CreateAPIKeyAdminResponse:
    """Generate API key."""
    service = AdminService(db)
    return await service.create_api_key(current_user.organization_id, req, current_user)


@router.delete(
    "/api-keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke Integration API Key",
    description="Revokes an active integration API key and records audit trail event.",
)
async def revoke_integration_api_key(
    key_id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    _: None = Depends(require_permission("api_keys:revoke")),
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """Revoke API key."""
    service = AdminService(db)
    await service.revoke_api_key(current_user.organization_id, key_id, current_user)


# ── Security & MFA Overview ────────────────────────────


@router.get(
    "/security/status",
    response_model=SecurityOverviewAdminResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Security Posture & MFA Overview",
    description="Returns security configuration overview, MFA enrollment metrics, and audit status.",
)
async def get_security_overview(
    current_user: UserModel = Depends(get_current_user_or_api_key),
    _: None = Depends(require_permission("organization:read")),
    db: AsyncSession = Depends(get_async_session),
) -> SecurityOverviewAdminResponse:
    """Retrieve security overview."""
    service = AdminService(db)
    return await service.get_security_overview(current_user.organization_id)
