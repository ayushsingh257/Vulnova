"""API Key Application Services & Use Cases."""

from datetime import datetime, timedelta, timezone
from typing import List, Tuple
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.api_keys.dto import (
    APIKeyCreateResponse,
    APIKeyResponse,
    CreateAPIKeyRequest,
)
from app.application.audit_logs.services import AuditLogService
from app.core.exceptions import ResourceNotFoundException, UnauthorizedException
from app.core.logging import get_logger
from app.infrastructure.database.models.api_key import APIKeyModel
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.api_key_repository import (
    APIKeyRepository,
)
from app.security.api_key import PREFIX_LENGTH, generate_api_key, hash_api_key

logger = get_logger("vulnova.api_keys")


class APIKeyService:
    """API Key Application Use Case Service handling creation, authentication, listing, and revocation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = APIKeyRepository(session)
        self.audit_service = AuditLogService(session)

    async def create_api_key(
        self, req: CreateAPIKeyRequest, user: UserModel
    ) -> APIKeyCreateResponse:
        """Create a new machine-to-machine integration API key for the user's organization.

        Raw key is generated and returned ONLY ONCE in the response DTO.
        Only key_prefix and SHA-256 key_hash are persisted in the database.
        """
        raw_key, key_prefix, key_hash = generate_api_key()

        now = datetime.now(timezone.utc)
        expires_at = None
        if req.expires_in_days:
            expires_at = now + timedelta(days=req.expires_in_days)

        key_model = APIKeyModel(
            id=uuid4(),
            organization_id=user.organization_id,
            user_id=user.id,
            name=req.name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            scopes=req.scopes,
            expires_at=expires_at,
            created_at=now,
        )

        key_model = await self.repo.create(key_model)

        logger.info(
            "api_key.created",
            api_key_id=str(key_model.id),
            user_id=str(user.id),
            organization_id=str(user.organization_id),
            key_prefix=key_prefix,
            name=req.name,
            scopes=req.scopes,
        )
        await self.audit_service.record_event(
            organization_id=user.organization_id,
            action="api_key.created",
            resource_type="api_key",
            resource_id=str(key_model.id),
            actor_user_id=user.id,
            details={"name": req.name, "key_prefix": key_prefix, "scopes": req.scopes},
        )

        return APIKeyCreateResponse(
            id=key_model.id,
            organization_id=key_model.organization_id,
            user_id=key_model.user_id,
            name=key_model.name,
            key_prefix=key_model.key_prefix,
            raw_key=raw_key,
            scopes=key_model.scopes,
            expires_at=key_model.expires_at,
            created_at=key_model.created_at,
        )

    async def authenticate_api_key(self, raw_key: str) -> Tuple[APIKeyModel, UserModel]:
        """Authenticate a raw API key string against stored SHA-256 hashes.

        Enforces format checks, revocation checks, expiration checks, and user/org active state.

        Returns:
            Tuple of (APIKeyModel, UserModel) if valid.

        Raises:
            UnauthorizedException: If key format is invalid, expired, revoked, or account inactive.
        """
        if not raw_key or len(raw_key) < PREFIX_LENGTH:
            logger.warning(
                "api_key.authentication_failed",
                reason="invalid_format",
            )
            raise UnauthorizedException("Invalid API key format")

        key_hash = hash_api_key(raw_key)
        key_record = await self.repo.get_by_hash(key_hash, load_relationships=True)

        if not key_record:
            logger.warning(
                "api_key.authentication_failed",
                reason="key_not_found_or_revoked",
                key_prefix=raw_key[:PREFIX_LENGTH],
            )
            raise UnauthorizedException("Invalid or revoked API key")

        # Expiration Check
        now = datetime.now(timezone.utc)
        if key_record.expires_at and key_record.expires_at < now:
            logger.warning(
                "api_key.authentication_failed",
                reason="expired",
                api_key_id=str(key_record.id),
                user_id=str(key_record.user_id),
            )
            raise UnauthorizedException("API key has expired")

        # Account Active Check
        if not key_record.user or not key_record.user.is_active:
            logger.warning(
                "api_key.authentication_failed",
                reason="user_inactive",
                api_key_id=str(key_record.id),
                user_id=str(key_record.user_id),
            )
            raise UnauthorizedException(
                "User account associated with API key is inactive"
            )

        if not key_record.organization or not key_record.organization.is_active:
            logger.warning(
                "api_key.authentication_failed",
                reason="organization_inactive",
                api_key_id=str(key_record.id),
                organization_id=str(key_record.organization_id),
            )
            raise UnauthorizedException(
                "Organization account associated with API key is inactive"
            )

        # Update last_used_at timestamp
        await self.repo.update_last_used(key_record.id)

        logger.info(
            "api_key.authentication_success",
            api_key_id=str(key_record.id),
            user_id=str(key_record.user_id),
            organization_id=str(key_record.organization_id),
        )

        return key_record, key_record.user

    async def list_api_keys(self, organization_id: UUID) -> List[APIKeyResponse]:
        """List all active API keys for an organization."""
        keys = await self.repo.list_by_organization(organization_id)
        return [APIKeyResponse.model_validate(k) for k in keys]

    async def revoke_api_key(
        self, key_id: UUID, organization_id: UUID, current_user_id: UUID
    ) -> None:
        """Revoke an API key with strict tenant organization boundary checks.

        Raises:
            ResourceNotFoundException: If key does not exist in the caller's organization.
        """
        deleted = await self.repo.delete(key_id, organization_id)
        if not deleted:
            raise ResourceNotFoundException(
                f"API key with ID '{key_id}' was not found in your organization"
            )

        logger.info(
            "api_key.revoked",
            api_key_id=str(key_id),
            organization_id=str(organization_id),
            revoked_by_user_id=str(current_user_id),
        )
        await self.audit_service.record_event(
            organization_id=organization_id,
            action="api_key.revoked",
            resource_type="api_key",
            resource_id=str(key_id),
            actor_user_id=current_user_id,
            details={"revoked_key_id": str(key_id)},
        )
