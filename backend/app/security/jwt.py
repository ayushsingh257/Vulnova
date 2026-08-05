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
    """Decode and validate a JWT access token."""
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
        raise UnauthorizedException("Invalid access token") from err


def create_mfa_login_token(
    user_id: UUID,
    organization_id: UUID,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a short-lived signed JWT MFA challenge token (valid for 5 minutes)."""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=5))
    payload: Dict[str, Any] = {
        "sub": str(user_id),
        "user_id": str(user_id),
        "organization_id": str(organization_id),
        "token_type": "mfa_challenge",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_mfa_login_token(token: str) -> Dict[str, Any]:
    """Decode and validate a short-lived MFA challenge token."""
    try:
        payload: Dict[str, Any] = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("token_type") != "mfa_challenge":
            raise UnauthorizedException("Invalid MFA challenge token type")
        return payload
    except jwt.ExpiredSignatureError as err:
        raise UnauthorizedException("MFA challenge token has expired") from err
    except jwt.PyJWTError as err:
        raise UnauthorizedException("Invalid MFA challenge token") from err


def hash_token(token_str: str) -> str:
    """Generate SHA-256 hex digest of a token string."""
    return hashlib.sha256(token_str.encode("utf-8")).hexdigest()
