"""FastAPI API Key & Dual-Mode Authentication Dependencies."""

from typing import Optional

from fastapi import Depends, Header, Request
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.application.api_keys.services import APIKeyService
from app.core.exceptions import UnauthorizedException
from app.core.logging import get_logger
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

logger = get_logger("vulnova.auth_dependency")

# OpenAPI Security Scheme for X-API-Key header
api_key_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key_user(
    x_api_key: Optional[str] = Depends(api_key_header_scheme),
    session: AsyncSession = Depends(get_async_session),
) -> UserModel:
    """Dependency injecting authenticated UserModel via X-API-Key header.

    Raises:
        UnauthorizedException: If X-API-Key header is missing or key is invalid.
    """
    if not x_api_key:
        raise UnauthorizedException("X-API-Key header is required")

    service = APIKeyService(session)
    _, user = await service.authenticate_api_key(x_api_key)
    return user


async def get_current_user_or_api_key(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    session: AsyncSession = Depends(get_async_session),
) -> UserModel:
    """Dual-mode authentication dependency.

    Authentication Priority Order:
    1. Bearer JWT authentication (via Authorization: Bearer <jwt>)
    2. X-API-Key header authentication fallback (via X-API-Key: <key>)

    If both headers are present:
    - Prefers JWT Bearer token
    - Logs authentication method choice via structlog

    Raises:
        UnauthorizedException: If neither header is present or authentication fails.
    """
    # 1. Check Bearer JWT Header Priority
    if authorization and authorization.lower().startswith("bearer "):
        if x_api_key:
            logger.info(
                "dual_auth_both_headers_present_preferring_jwt",
                auth_method="jwt_bearer",
            )
        else:
            logger.debug("authenticating_via_jwt_bearer", auth_method="jwt_bearer")

        token = authorization.split(" ", 1)[1].strip()
        return await get_current_user(token=token, session=session)

    # 2. Check X-API-Key Header Fallback
    if x_api_key:
        logger.debug("authenticating_via_api_key", auth_method="x_api_key")
        service = APIKeyService(session)
        _, user = await service.authenticate_api_key(x_api_key)
        return user

    # 3. Neither Header Present
    logger.warning("authentication_failed_missing_credentials")
    raise UnauthorizedException(
        "Authentication required via 'Authorization: Bearer <token>' or 'X-API-Key: <key>'"
    )
