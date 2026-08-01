"""Vulnova JWT Token Provider & Cryptographic Token Hashing Adapter."""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import UUID

import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedException


def create_access_token(
    user_id: UUID,
    organization_id: UUID,
    role: str,
    subject: Optional[str] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token.

    Args:
        user_id: The UUID of the user.
        organization_id: The UUID of the organization tenant.
        role: The user's role in the organization.
        subject: Optional token subject (defaults to user_id string).
        expires_delta: Optional custom token expiration timedelta.

    Returns:
        Encoded JWT access token string signed with HS256.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    payload: Dict[str, Any] = {
        "sub": subject or str(user_id),
        "user_id": str(user_id),
        "organization_id": str(organization_id),
        "role": role,
        "token_type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    encoded_jwt: str = jwt.encode(
        payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token.

    Args:
        token: Encoded JWT access token string.

    Returns:
        Decoded claims dictionary if valid.

    Raises:
        UnauthorizedException: If token is expired or invalid.
    """
    try:
        payload: Dict[str, Any] = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("token_type") != "access":
            raise UnauthorizedException("Invalid token type")
        return payload
    except jwt.ExpiredSignatureError as err:
        raise UnauthorizedException("Access token has expired") from err
    except jwt.PyJWTError as err:
        raise UnauthorizedException(f"Invalid access token: {str(err)}") from err


def hash_token(token_str: str) -> str:
    """Hash a token string (e.g. refresh token) using SHA-256 for secure database storage.

    Args:
        token_str: The raw token string.

    Returns:
        SHA-256 hex digest string.
    """
    return hashlib.sha256(token_str.encode("utf-8")).hexdigest()
