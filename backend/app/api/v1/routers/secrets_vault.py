"""FastAPI REST Router for Phase 12.8 Enterprise Secrets Vault & KMS Credential Governance."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.rbac import require_permission
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session
from app.infrastructure.secrets_vault.dto import (
    CreateSecretRequestDTO,
    KMSHealthDTO,
    RotateSecretRequestDTO,
    SecretDecryptedDTO,
    SecretResponseDTO,
    SecretRotationStatusDTO,
)
from app.infrastructure.secrets_vault.kms_health_service import (
    KMSHealthService,
)
from app.infrastructure.secrets_vault.provider_registry import (
    kms_registry,
)
from app.infrastructure.secrets_vault.rotation_service import (
    SecretRotationService,
)
from app.infrastructure.secrets_vault.vault_service import (
    SecretVaultService,
)

router = APIRouter(
    prefix="/secrets",
    tags=["Enterprise Secrets Vault & KMS Governance Architecture"],
)


@router.post(
    "",
    response_model=SecretResponseDTO,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("secrets:manage"))],
)
async def store_secret(
    payload: CreateSecretRequestDTO,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> SecretResponseDTO:
    """Store a new envelope-encrypted enterprise secret in the vault."""
    service = SecretVaultService(session)
    return await service.store_secret(
        request=payload,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
    )


@router.get(
    "",
    response_model=List[SecretResponseDTO],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("secrets:read"))],
)
async def list_secrets(
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> List[SecretResponseDTO]:
    """List non-sensitive metadata for enterprise secrets in organization."""
    service = SecretVaultService(session)
    items, _ = await service.list_secrets(
        organization_id=current_user.organization_id,
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    return items


@router.get(
    "/rotation-status",
    response_model=SecretRotationStatusDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("secrets:read"))],
)
async def get_rotation_status(
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> SecretRotationStatusDTO:
    """Retrieve rotation compliance and expiration posture metrics."""
    service = SecretRotationService(session)
    return await service.get_rotation_posture(
        organization_id=current_user.organization_id
    )


@router.get(
    "/providers",
    response_model=List[str],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("secrets:read"))],
)
async def list_kms_providers(
    current_user: UserModel = Depends(get_current_user_or_api_key),
) -> List[str]:
    """List supported Key Management System provider drivers."""
    return kms_registry.list_supported_providers()


@router.get(
    "/kms-health",
    response_model=List[KMSHealthDTO],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("secrets:read"))],
)
async def get_kms_health(
    current_user: UserModel = Depends(get_current_user_or_api_key),
) -> List[KMSHealthDTO]:
    """Perform live health diagnosis on configured KMS providers."""
    return await KMSHealthService.check_all_providers()


@router.get(
    "/{id}",
    response_model=SecretResponseDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("secrets:read"))],
)
async def get_secret_metadata(
    id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> SecretResponseDTO:
    """Fetch secret metadata and rotation policy."""
    service = SecretVaultService(session)
    return await service.get_secret_metadata(
        secret_id=id, organization_id=current_user.organization_id
    )


@router.post(
    "/{id}/access",
    response_model=SecretDecryptedDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("secrets:access"))],
)
async def access_secret_plaintext(
    id: UUID,
    request: Request,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> SecretDecryptedDTO:
    """Decrypt and access plaintext secret with mandatory audit log attribution."""
    service = SecretVaultService(session)
    client_ip = request.client.host if request.client else None
    return await service.access_secret_plaintext(
        secret_id=id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        client_ip=client_ip,
    )


@router.post(
    "/{id}/rotate",
    response_model=SecretResponseDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("secrets:rotate"))],
)
async def rotate_secret(
    id: UUID,
    payload: RotateSecretRequestDTO,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> SecretResponseDTO:
    """Rotate an existing secret by re-encrypting with a fresh DEK."""
    service = SecretRotationService(session)
    return await service.rotate_secret(
        secret_id=id,
        organization_id=current_user.organization_id,
        new_plaintext_value=payload.new_plaintext_value,
        actor_user_id=current_user.id,
        reason=payload.reason,
    )


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("secrets:manage"))],
)
async def delete_secret(
    id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    """Permanently delete a secret from the enterprise vault."""
    service = SecretVaultService(session)
    await service.delete_secret(
        secret_id=id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
    )
