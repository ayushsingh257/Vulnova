"""FastAPI Router for API Key Management (/api/v1/api-keys)."""

from typing import Dict
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_active_user
from app.api.v1.dependencies.rbac import require_permission
from app.application.api_keys.dto import (
    APIKeyCreateResponse,
    APIKeyListResponse,
    CreateAPIKeyRequest,
)
from app.application.api_keys.services import APIKeyService
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

router = APIRouter(prefix="/api-keys", tags=["API Keys & Integrations"])


@router.post(
    "",
    response_model=APIKeyCreateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("api_keys:create"))],
)
async def create_api_key(
    req: CreateAPIKeyRequest,
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> APIKeyCreateResponse:
    """Create a new machine-to-machine integration API key for the user's organization.

    Note:
        The raw API key string is returned ONLY ONCE in this creation response.
        Store it securely; it is unrecoverable after creation.
    """
    service = APIKeyService(session)
    return await service.create_api_key(req, current_user)


@router.get(
    "",
    response_model=APIKeyListResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("api_keys:read"))],
)
async def list_api_keys(
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> APIKeyListResponse:
    """List all active API keys for the authenticated user's organization."""
    service = APIKeyService(session)
    keys = await service.list_api_keys(current_user.organization_id)
    return APIKeyListResponse(api_keys=keys, total=len(keys))


@router.delete(
    "/{key_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("api_keys:revoke"))],
)
async def revoke_api_key(
    key_id: UUID,
    current_user: UserModel = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, str]:
    """Revoke an API key belonging to the user's organization."""
    service = APIKeyService(session)
    await service.revoke_api_key(
        key_id=key_id,
        organization_id=current_user.organization_id,
        current_user_id=current_user.id,
    )
    return {"message": "API key revoked successfully"}
