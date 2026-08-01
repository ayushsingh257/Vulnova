"""FastAPI Authentication & User Injection Dependencies."""

from uuid import UUID

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import UnauthorizedException
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.database.session import get_async_session
from app.security.jwt import decode_access_token

# OAuth2 Password Bearer scheme pointing to login endpoint
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/login", auto_error=True
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_async_session),
) -> UserModel:
    """Dependency injector validating JWT access token and returning current UserModel.

    Raises:
        UnauthorizedException: If token is invalid/expired or user is inactive/not found.
    """
    payload = decode_access_token(token)
    user_id_str = payload.get("user_id") or payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException("Invalid token payload: missing user_id")

    try:
        user_id = UUID(user_id_str)
    except ValueError as err:
        raise UnauthorizedException(
            "Invalid token payload: invalid UUID format"
        ) from err

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id, load_organization=True)
    if not user:
        raise UnauthorizedException("User associated with token no longer exists")

    if not user.is_active:
        raise UnauthorizedException("User account is inactive")

    return user


async def get_current_active_user(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    """Dependency injector ensuring current user is active."""
    return current_user
