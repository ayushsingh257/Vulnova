"""Auth Application Services & Use Cases."""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Tuple
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.application.auth.dto import (
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.core.exceptions import (
    UnauthorizedException,
    ValidationException,
)
from app.core.logging import get_logger
from app.infrastructure.database.models.organization import OrganizationModel
from app.infrastructure.database.models.refresh_token import RefreshTokenModel
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.organization_repository import (
    OrganizationRepository,
)
from app.infrastructure.database.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.security.jwt import create_access_token, create_mfa_login_token, hash_token
from app.security.password import hash_password, verify_password

logger = get_logger("vulnova.auth")

REFRESH_TOKEN_EXPIRE_DAYS = 7


class AuthService:
    """Authentication Application Use Case Service handling user registration, authentication, token rotation, and logout."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.org_repo = OrganizationRepository(session)
        self.refresh_repo = RefreshTokenRepository(session)
        self.audit_service = AuditLogService(session)

    async def register(
        self, req: RegisterRequest
    ) -> Tuple[UserModel, OrganizationModel]:
        """Register a new organization tenant and its initial Owner user.

        Raises:
            ValidationException: If email or organization slug is already registered.
        """
        existing_org = await self.org_repo.get_by_slug(req.organization_slug)
        if existing_org:
            raise ValidationException(
                f"Organization slug '{req.organization_slug}' is already taken."
            )

        existing_user = await self.user_repo.get_by_email(req.email)
        if existing_user:
            raise ValidationException(
                f"User email '{req.email}' is already registered."
            )

        # 1. Create Organization
        now = datetime.now(timezone.utc)
        org = OrganizationModel(
            id=uuid4(),
            name=req.organization_name,
            slug=req.organization_slug,
            plan_tier="ENTERPRISE_TRIAL",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        org = await self.org_repo.create(org)

        # 2. Create Owner User
        hashed_pwd = hash_password(req.password)
        user = UserModel(
            id=uuid4(),
            organization_id=org.id,
            email=req.email,
            password_hash=hashed_pwd,
            full_name=req.full_name,
            role="OWNER",
            is_active=True,
            is_mfa_enabled=False,
            created_at=now,
            updated_at=now,
        )
        user = await self.user_repo.create(user)

        logger.info(
            "user_registered",
            user_id=str(user.id),
            email=user.email,
            org_id=str(org.id),
            org_slug=org.slug,
        )
        await self.audit_service.record_event(
            organization_id=org.id,
            action="auth.registered",
            resource_type="organization",
            resource_id=str(org.id),
            actor_user_id=user.id,
            details={"email": user.email, "org_name": org.name},
        )
        return user, org

    async def login(self, email: str, password: str) -> Tuple[TokenResponse, str]:
        """Authenticate user credentials and issue access and refresh tokens.

        Returns:
            Tuple of (TokenResponse, raw_refresh_token_string)

        Raises:
            UnauthorizedException: If email/password is invalid or user is inactive.
        """
        user = await self.user_repo.get_by_email(email, load_organization=True)
        if not user or not verify_password(password, user.password_hash):
            logger.warning("login_failed_invalid_credentials", email=email)
            if user:
                await self.audit_service.record_event(
                    organization_id=user.organization_id,
                    action="auth.login_failed",
                    resource_type="user",
                    resource_id=str(user.id),
                    details={"email": email, "reason": "invalid_credentials"},
                )
            raise UnauthorizedException("Invalid email or password.")

        if not user.is_active:
            logger.warning("login_failed_inactive_user", user_id=str(user.id))
            await self.audit_service.record_event(
                organization_id=user.organization_id,
                action="auth.login_failed",
                resource_type="user",
                resource_id=str(user.id),
                actor_user_id=user.id,
                details={"email": email, "reason": "user_inactive"},
            )
            raise UnauthorizedException("User account is inactive.")

        if user.mfa_enabled:
            mfa_login_token = create_mfa_login_token(
                user_id=user.id,
                organization_id=user.organization_id,
            )
            return (
                TokenResponse(
                    access_token="",
                    token_type="bearer",
                    user=None,
                    mfa_required=True,
                    mfa_login_token=mfa_login_token,
                ),
                "",
            )

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
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=REFRESH_TOKEN_EXPIRE_DAYS
        )

        refresh_model = RefreshTokenModel(
            user_id=user.id,
            family_id=family_id,
            token_hash=hashed_rt,
            expires_at=expires_at,
        )
        await self.refresh_repo.create(refresh_model)
        await self.user_repo.update_last_login(user.id)

        await self.audit_service.record_event(
            organization_id=user.organization_id,
            action="auth.login_success",
            resource_type="user",
            resource_id=str(user.id),
            actor_user_id=user.id,
            details={"email": user.email, "role": user.role},
        )

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

        token_response = TokenResponse(
            access_token=access_token, token_type="bearer", user=user_response
        )

        logger.info(
            "login_success", user_id=str(user.id), org_id=str(user.organization_id)
        )
        return token_response, raw_refresh_token

    async def refresh(self, raw_refresh_token: str) -> Tuple[TokenResponse, str]:
        """Rotate refresh token and issue a new access token.

        Enforces token family reuse detection: if an already revoked token is used,
        the entire token family is revoked to prevent token theft.

        Returns:
            Tuple of (TokenResponse, new_raw_refresh_token_string)

        Raises:
            UnauthorizedException: If token is invalid, expired, or revoked.
        """
        hashed_rt = hash_token(raw_refresh_token)
        token_record = await self.refresh_repo.get_by_hash(hashed_rt)

        if not token_record:
            logger.warning("token_refresh_failed_not_found")
            raise UnauthorizedException("Invalid refresh token.")

        # REUSE DETECTION: If token is already revoked, breach detected! Revoke entire family.
        if token_record.is_revoked:
            logger.error(
                "token_reuse_detected",
                family_id=str(token_record.family_id),
                user_id=str(token_record.user_id),
            )
            await self.refresh_repo.revoke_family(token_record.family_id)
            raise UnauthorizedException(
                "Refresh token reuse detected. Access revoked for security."
            )

        # Expiration Check
        now = datetime.now(timezone.utc)
        if token_record.expires_at < now:
            logger.warning(
                "token_refresh_failed_expired", user_id=str(token_record.user_id)
            )
            await self.refresh_repo.revoke_by_hash(hashed_rt)
            raise UnauthorizedException("Refresh token has expired.")

        # Revoke current token
        await self.refresh_repo.revoke_by_hash(hashed_rt)

        # Retrieve User
        user = await self.user_repo.get_by_id(
            token_record.user_id, load_organization=True
        )
        if not user or not user.is_active:
            raise UnauthorizedException("User account is inactive or not found.")

        # Generate new access token
        access_token = create_access_token(
            user_id=user.id,
            organization_id=user.organization_id,
            role=user.role,
            subject=str(user.id),
        )

        # Issue new refresh token in SAME family_id
        new_raw_refresh_token = secrets.token_urlsafe(64)
        new_hashed_rt = hash_token(new_raw_refresh_token)
        new_expires_at = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        new_refresh_model = RefreshTokenModel(
            user_id=user.id,
            family_id=token_record.family_id,
            token_hash=new_hashed_rt,
            expires_at=new_expires_at,
        )
        await self.refresh_repo.create(new_refresh_model)

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

        token_response = TokenResponse(
            access_token=access_token, token_type="bearer", user=user_response
        )

        logger.info(
            "token_refreshed_success",
            user_id=str(user.id),
            family_id=str(token_record.family_id),
        )
        return token_response, new_raw_refresh_token

    async def logout(self, raw_refresh_token: str) -> None:
        """Revoke a refresh token on logout."""
        if not raw_refresh_token:
            return
        hashed_rt = hash_token(raw_refresh_token)
        await self.refresh_repo.revoke_by_hash(hashed_rt)
        logger.info("logout_success")
