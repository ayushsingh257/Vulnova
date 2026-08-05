"""FastAPI REST Router for Multi-Factor Authentication (MFA / TOTP) (/api/v1/auth/mfa)."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated, Dict
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.application.audit_logs.services import AuditLogService
from app.application.auth.dto import TokenResponse, UserResponse
from app.application.mfa.dto import (
    MFAChallengeRequest,
    MFADisableRequest,
    MFARecoveryRegenerateRequest,
    MFARecoveryRegenerateResponse,
    MFASetupResponse,
    MFAStatusResponse,
    MFAVerifySetupRequest,
)
from app.application.mfa.mfa_service import MFAService
from app.infrastructure.database.models.refresh_token import RefreshTokenModel
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.database.session import get_async_session
from app.security.jwt import create_access_token, decode_mfa_login_token, hash_token

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth/mfa", tags=["Multi-Factor Authentication (MFA)"])

REFRESH_COOKIE_NAME = "vulnova_refresh_token"
REFRESH_COOKIE_MAX_AGE = 7 * 24 * 60 * 60  # 7 days in seconds


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Helper to set HTTP-Only secure refresh token cookie."""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=REFRESH_COOKIE_MAX_AGE,
        path="/api/v1/auth",
    )


def get_mfa_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> MFAService:
    """Dependency provider for MFAService."""
    audit_service = AuditLogService(session)
    return MFAService(session=session, audit_log_service=audit_service)


@router.post(
    "/setup",
    response_model=MFASetupResponse,
    status_code=status.HTTP_200_OK,
    summary="Initialize MFA TOTP Setup",
    description="Generates a new base32 TOTP secret, provisioning URI, Base64 QR code, and 10 single-use recovery codes.",
)
async def setup_mfa(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    mfa_service: Annotated[MFAService, Depends(get_mfa_service)],
) -> MFASetupResponse:
    """Initiate MFA setup for authenticated user."""
    return await mfa_service.initiate_mfa_setup(current_user)


@router.post(
    "/verify-setup",
    status_code=status.HTTP_200_OK,
    summary="Verify Setup & Enable MFA",
    description="Verifies the initial 6-digit OTP code to confirm authenticator app binding and activate MFA on account.",
)
async def verify_mfa_setup(
    req: MFAVerifySetupRequest,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    mfa_service: Annotated[MFAService, Depends(get_mfa_service)],
) -> Dict[str, str]:
    """Verify first OTP and activate MFA."""
    await mfa_service.verify_and_enable_mfa(current_user, req.code)
    return {
        "status": "enabled",
        "message": "Multi-Factor Authentication successfully activated.",
    }


@router.post(
    "/disable",
    status_code=status.HTTP_200_OK,
    summary="Disable MFA",
    description="Disables Multi-Factor Authentication. Requires current password and a valid 6-digit OTP code.",
)
async def disable_mfa(
    req: MFADisableRequest,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    mfa_service: Annotated[MFAService, Depends(get_mfa_service)],
) -> Dict[str, str]:
    """Disable MFA on user account."""
    await mfa_service.disable_mfa(current_user, req.current_password, req.code)
    return {
        "status": "disabled",
        "message": "Multi-Factor Authentication has been disabled.",
    }


@router.post(
    "/challenge",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="MFA Login Challenge Verification",
    description="Verifies 6-digit OTP code or single-use recovery code during login challenge, issuing session access & refresh tokens.",
)
async def verify_mfa_login_challenge(
    req: MFAChallengeRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    mfa_service: Annotated[MFAService, Depends(get_mfa_service)],
) -> TokenResponse:
    """Verify MFA code during login and issue session tokens."""
    # Decode ephemeral MFA login challenge token
    payload = decode_mfa_login_token(req.mfa_login_token)
    user_id_str = payload.get("user_id")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA challenge token claims.",
        )

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(UUID(user_id_str), load_organization=True)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account unavailable or inactive.",
        )

    # Verify code (TOTP or recovery)
    await mfa_service.verify_mfa_challenge(user, req.code)

    # Issue Access Token
    access_token = create_access_token(
        user_id=user.id,
        organization_id=user.organization_id,
        role=user.role,
        subject=str(user.id),
    )

    # Issue Refresh Token in new family
    raw_refresh_token = secrets.token_urlsafe(64)
    hashed_rt = hash_token(raw_refresh_token)
    family_id = uuid4()
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    refresh_repo = RefreshTokenRepository(session)
    refresh_model = RefreshTokenModel(
        user_id=user.id,
        family_id=family_id,
        token_hash=hashed_rt,
        expires_at=expires_at,
    )
    await refresh_repo.create(refresh_model)
    await user_repo.update_last_login(user.id)

    _set_refresh_cookie(response, raw_refresh_token)

    user_response = UserResponse(
        id=user.id,
        organization_id=user.organization_id,
        organization_name=user.organization.name,
        organization_slug=user.organization.slug,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_mfa_enabled=user.is_mfa_enabled,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_response,
        mfa_required=False,
    )


@router.post(
    "/recovery-codes/regenerate",
    response_model=MFARecoveryRegenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="Regenerate Backup Recovery Codes",
    description="Regenerates a new set of 10 single-use recovery backup codes. Invalidates all previous backup codes.",
)
async def regenerate_recovery_codes(
    req: MFARecoveryRegenerateRequest,
    current_user: Annotated[UserModel, Depends(get_current_user)],
    mfa_service: Annotated[MFAService, Depends(get_mfa_service)],
) -> MFARecoveryRegenerateResponse:
    """Regenerate new backup recovery codes."""
    return await mfa_service.regenerate_recovery_codes(
        current_user, req.current_password, req.code
    )


@router.get(
    "/status",
    response_model=MFAStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get MFA Status",
    description="Returns current MFA configuration, last verification timestamp, and active backup codes count.",
)
async def get_mfa_status(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    mfa_service: Annotated[MFAService, Depends(get_mfa_service)],
) -> MFAStatusResponse:
    """Get MFA status for current user."""
    return mfa_service.get_mfa_status(current_user)
