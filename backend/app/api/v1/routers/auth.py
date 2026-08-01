"""FastAPI Router for Authentication & Token Management (/api/v1/auth)."""

from typing import Dict, Optional

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_active_user
from app.application.auth.dto import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.application.auth.services import AuthService
from app.core.exceptions import UnauthorizedException, ValidationException
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

router = APIRouter(prefix="/auth", tags=["Authentication & Access"])

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


def _clear_refresh_cookie(response: Response) -> None:
    """Helper to clear refresh token cookie."""
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/api/v1/auth",
    )


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register_organization_and_owner(
    req: RegisterRequest, session: AsyncSession = Depends(get_async_session)
) -> UserResponse:
    """Register a new tenant organization and its primary Owner user."""
    auth_service = AuthService(session)
    user, org = await auth_service.register(req)

    return UserResponse(
        id=user.id,
        organization_id=org.id,
        organization_name=org.name,
        organization_slug=org.slug,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_mfa_enabled=user.is_mfa_enabled,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_async_session),
) -> TokenResponse:
    """Authenticate user credentials and issue access token & refresh token cookie.

    Supports both JSON body payloads and standard OAuth2 form-data logins.
    """
    content_type = request.headers.get("content-type", "")
    email: Optional[str] = None
    password: Optional[str] = None

    if "application/json" in content_type:
        try:
            body = await request.json()
            login_req = LoginRequest.model_validate(body)
            email = login_req.email
            password = login_req.password
        except Exception as err:
            raise ValidationException("Invalid login JSON payload") from err
    else:
        form = await request.form()
        email = str(form.get("username") or form.get("email") or "")
        password = str(form.get("password") or "")

    if not email or not password:
        raise UnauthorizedException("Email and password are required")

    auth_service = AuthService(session)
    token_response, raw_refresh_token = await auth_service.login(email, password)

    _set_refresh_cookie(response, raw_refresh_token)
    return token_response


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh_tokens(
    response: Response,
    refresh_body: Optional[RefreshRequest] = None,
    vulnova_refresh_token: Optional[str] = Cookie(None),
    session: AsyncSession = Depends(get_async_session),
) -> TokenResponse:
    """Rotate refresh token and issue a new access token.

    Reads refresh token from HTTP-Only cookie or JSON request body.
    """
    raw_token = vulnova_refresh_token or (
        refresh_body.refresh_token if refresh_body else None
    )
    if not raw_token:
        raise UnauthorizedException("Refresh token is required")

    auth_service = AuthService(session)
    token_response, new_raw_refresh_token = await auth_service.refresh(raw_token)

    _set_refresh_cookie(response, new_raw_refresh_token)
    return token_response


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    response: Response,
    refresh_body: Optional[RefreshRequest] = None,
    vulnova_refresh_token: Optional[str] = Cookie(None),
    session: AsyncSession = Depends(get_async_session),
) -> Dict[str, str]:
    """Revoke refresh token and clear authentication cookie."""
    raw_token = vulnova_refresh_token or (
        refresh_body.refresh_token if refresh_body else None
    )
    if raw_token:
        auth_service = AuthService(session)
        await auth_service.logout(raw_token)

    _clear_refresh_cookie(response)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def get_current_user_profile(
    current_user: UserModel = Depends(get_current_active_user),
) -> UserResponse:
    """Retrieve authenticated user and organization profile."""
    return UserResponse(
        id=current_user.id,
        organization_id=current_user.organization_id,
        organization_name=current_user.organization.name,
        organization_slug=current_user.organization.slug,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        is_mfa_enabled=current_user.is_mfa_enabled,
        last_login_at=current_user.last_login_at,
        created_at=current_user.created_at,
    )
