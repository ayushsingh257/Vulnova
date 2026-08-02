"""FastAPI Router for User Management (/api/v1/users)."""

from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_active_user
from app.api.v1.dependencies.rbac import require_permission
from app.application.users.dto import (
    InviteUserRequest,
    UpdateUserProfileRequest,
    UpdateUserRoleRequest,
    UpdateUserStatusRequest,
    UserDetailResponse,
    UserListResponse,
)
from app.application.users.services import UserService
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get(
    "/me",
    response_model=UserDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def get_my_profile(
    current_user: UserModel = Depends(get_current_active_user),
) -> UserDetailResponse:
    """Get authenticated user's profile details."""
    return UserDetailResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def update_my_profile(
    req: UpdateUserProfileRequest,
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> UserDetailResponse:
    """Update authenticated user's own profile."""
    service = UserService(session)
    return await service.update_profile(current_user, req)


@router.get(
    "",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("users:read"))],
)
async def list_users(
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> UserListResponse:
    """List all members belonging to the authenticated user's organization."""
    service = UserService(session)
    return await service.list_organization_users(current_user.organization_id)


@router.get(
    "/{user_id}",
    response_model=UserDetailResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("users:read"))],
)
async def get_user_detail(
    user_id: UUID,
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> UserDetailResponse:
    """Get details of a specific team member within the organization."""
    service = UserService(session)
    return await service.get_user_detail(
        user_id=user_id, organization_id=current_user.organization_id
    )


@router.post(
    "",
    response_model=UserDetailResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("users:invite"))],
)
async def create_user(
    req: InviteUserRequest,
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> UserDetailResponse:
    """Create / invite a new member into the organization."""
    service = UserService(session)
    return await service.invite_user(req, current_user)


@router.patch(
    "/{user_id}/role",
    response_model=UserDetailResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("users:update_role"))],
)
async def update_user_role(
    user_id: UUID,
    req: UpdateUserRoleRequest,
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> UserDetailResponse:
    """Modify a team member's role (OWNER-only privilege)."""
    service = UserService(session)
    return await service.update_user_role(user_id, req, current_user)


@router.patch(
    "/{user_id}/status",
    response_model=UserDetailResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("users:remove"))],
)
async def update_user_status(
    user_id: UUID,
    req: UpdateUserStatusRequest,
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> UserDetailResponse:
    """Activate or deactivate a team member's account."""
    service = UserService(session)
    return await service.update_user_status(user_id, req, current_user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("users:remove"))],
)
async def remove_user(
    user_id: UUID,
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """Remove a member from the organization."""
    service = UserService(session)
    await service.remove_user(user_id, current_user)
    return {"message": "User removed successfully"}
