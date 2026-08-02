"""FastAPI Router for Organization Management (/api/v1/organizations)."""

from typing import Any, Dict

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_active_user
from app.api.v1.dependencies.rbac import require_permission
from app.application.organizations.dto import (
    OrganizationDetailResponse,
    UpdateOrganizationRequest,
)
from app.application.organizations.services import OrganizationService
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

router = APIRouter(prefix="/organizations", tags=["Organization Management"])


@router.get(
    "/me",
    response_model=OrganizationDetailResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("organization:read"))],
)
async def get_my_organization(
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> OrganizationDetailResponse:
    """Get authenticated user's organization profile and active member count."""
    service = OrganizationService(session)
    return await service.get_organization(current_user.organization_id)


@router.patch(
    "/me",
    response_model=OrganizationDetailResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("organization:update"))],
)
async def update_my_organization(
    req: UpdateOrganizationRequest,
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> OrganizationDetailResponse:
    """Update authenticated user's organization settings (name, plan_tier)."""
    service = OrganizationService(session)
    return await service.update_organization(
        organization_id=current_user.organization_id,
        req=req,
        current_user=current_user,
    )


@router.delete(
    "/me",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("organization:delete"))],
)
async def deactivate_my_organization(
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, Any]:
    """Deactivate organization account (OWNER-only action)."""
    service = OrganizationService(session)
    await service.deactivate_organization(
        organization_id=current_user.organization_id,
        current_user=current_user,
    )
    return {"message": "Organization deactivated successfully"}
