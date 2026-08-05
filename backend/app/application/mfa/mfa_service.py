"""MFA Application Service orchestrating TOTP enrollment, challenge verification, and recovery management."""

import json
from datetime import datetime, timezone

import structlog
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.application.mfa.dto import (
    MFARecoveryRegenerateResponse,
    MFASetupResponse,
    MFAStatusResponse,
)
from app.application.mfa.recovery_service import RecoveryService
from app.application.mfa.totp_service import TOTPService
from app.infrastructure.database.models.user import UserModel
from app.security.encryption import CryptoService
from app.security.password import verify_password

logger = structlog.get_logger(__name__)


class MFAService:
    """Enterprise MFA Service managing user TOTP lifecycle & recovery codes."""

    def __init__(
        self,
        session: AsyncSession,
        audit_log_service: AuditLogService,
    ) -> None:
        self.session = session
        self.audit_log_service = audit_log_service

    async def initiate_mfa_setup(self, user: UserModel) -> MFASetupResponse:
        """Initialize MFA setup for user, generating encrypted TOTP secret and backup recovery codes."""
        # Generate new base32 secret & recovery codes
        raw_secret = TOTPService.generate_secret()
        recovery_codes = RecoveryService.generate_recovery_codes(10)
        hashed_recovery_codes = RecoveryService.hash_recovery_codes(recovery_codes)

        # Encrypt TOTP secret using AES-256-GCM
        encrypted_secret = CryptoService.encrypt(raw_secret)

        # Save pending setup to user (MFA remains disabled until verify_and_enable_mfa)
        user.mfa_secret = encrypted_secret
        user.mfa_backup_codes = json.dumps(hashed_recovery_codes)
        await self.session.commit()

        # Build provisioning URI & QR Code
        provisioning_uri = TOTPService.get_provisioning_uri(raw_secret, user.email)
        qr_code_base64 = TOTPService.generate_qr_code_base64(provisioning_uri)

        return MFASetupResponse(
            secret=raw_secret,
            provisioning_uri=provisioning_uri,
            qr_code_base64=qr_code_base64,
            recovery_codes=recovery_codes,
        )

    async def verify_and_enable_mfa(self, user: UserModel, code: str) -> bool:
        """Verify the first OTP code during setup to confirm authenticator binding and activate MFA."""
        if not user.mfa_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MFA setup has not been initiated. Please run setup first.",
            )

        raw_secret = CryptoService.decrypt(user.mfa_secret)
        if not TOTPService.verify_totp_code(raw_secret, code):
            await self.audit_log_service.record_event(
                organization_id=user.organization_id,
                action="security.mfa_verification_failed",
                resource_type="user",
                resource_id=str(user.id),
                actor_user_id=user.id,
                details={"reason": "Invalid TOTP code during initial activation"},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid 6-digit OTP code. Please check your authenticator app time and try again.",
            )

        now_utc = datetime.now(timezone.utc)
        user.mfa_enabled = True
        user.mfa_verified_at = now_utc
        user.mfa_last_used_at = now_utc
        await self.session.commit()

        await self.audit_log_service.record_event(
            organization_id=user.organization_id,
            action="security.mfa_enabled",
            resource_type="user",
            resource_id=str(user.id),
            actor_user_id=user.id,
            details={"mfa_verified_at": now_utc.isoformat()},
        )

        return True

    async def verify_mfa_challenge(self, user: UserModel, code: str) -> bool:
        """Verify OTP code or single-use recovery code during login challenge."""
        if not user.mfa_enabled or not user.mfa_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MFA is not enabled for this account.",
            )

        code_clean = code.strip()

        # Check if 6-digit TOTP code
        if code_clean.isdigit() and len(code_clean) == 6:
            raw_secret = CryptoService.decrypt(user.mfa_secret)
            if TOTPService.verify_totp_code(raw_secret, code_clean):
                now_utc = datetime.now(timezone.utc)
                user.mfa_last_used_at = now_utc
                await self.session.commit()

                await self.audit_log_service.record_event(
                    organization_id=user.organization_id,
                    action="security.mfa_verification_success",
                    resource_type="user",
                    resource_id=str(user.id),
                    actor_user_id=user.id,
                    details={"method": "totp"},
                )
                return True

        # Check if single-use recovery code
        if user.mfa_backup_codes:
            is_valid, updated_json, remaining = RecoveryService.verify_and_consume(
                user.mfa_backup_codes, code_clean
            )
            if is_valid:
                now_utc = datetime.now(timezone.utc)
                user.mfa_backup_codes = updated_json
                user.mfa_last_used_at = now_utc
                await self.session.commit()

                await self.audit_log_service.record_event(
                    organization_id=user.organization_id,
                    action="security.mfa_recovery_used",
                    resource_type="user",
                    resource_id=str(user.id),
                    actor_user_id=user.id,
                    details={"remaining_codes": remaining},
                )
                await self.audit_log_service.record_event(
                    organization_id=user.organization_id,
                    action="security.mfa_verification_success",
                    resource_type="user",
                    resource_id=str(user.id),
                    actor_user_id=user.id,
                    details={"method": "recovery_code"},
                )
                return True

        # Verification failed
        await self.audit_log_service.record_event(
            organization_id=user.organization_id,
            action="security.mfa_verification_failed",
            resource_type="user",
            resource_id=str(user.id),
            actor_user_id=user.id,
            details={"reason": "Invalid TOTP code or recovery code"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication code or recovery code.",
        )

    async def disable_mfa(
        self, user: UserModel, current_password: str, code: str
    ) -> bool:
        """Disable MFA requiring password re-authentication and valid OTP code."""
        if not user.mfa_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MFA is not currently enabled for this account.",
            )

        if not verify_password(current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid current password.",
            )

        raw_secret = CryptoService.decrypt(user.mfa_secret or "")
        if not TOTPService.verify_totp_code(raw_secret, code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid 6-digit OTP code.",
            )

        user.mfa_enabled = False
        user.mfa_secret = None
        user.mfa_backup_codes = None
        user.mfa_verified_at = None
        await self.session.commit()

        await self.audit_log_service.record_event(
            organization_id=user.organization_id,
            action="security.mfa_disabled",
            resource_type="user",
            resource_id=str(user.id),
            actor_user_id=user.id,
            details={"disabled_at": datetime.now(timezone.utc).isoformat()},
        )

        return True

    async def regenerate_recovery_codes(
        self, user: UserModel, current_password: str, code: str
    ) -> MFARecoveryRegenerateResponse:
        """Regenerate new backup recovery codes requiring password & OTP verification."""
        if not user.mfa_enabled or not user.mfa_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="MFA must be enabled to regenerate recovery codes.",
            )

        if not verify_password(current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid current password.",
            )

        raw_secret = CryptoService.decrypt(user.mfa_secret)
        if not TOTPService.verify_totp_code(raw_secret, code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid 6-digit OTP code.",
            )

        new_codes = RecoveryService.generate_recovery_codes(10)
        hashed_codes = RecoveryService.hash_recovery_codes(new_codes)
        user.mfa_backup_codes = json.dumps(hashed_codes)
        await self.session.commit()

        await self.audit_log_service.record_event(
            organization_id=user.organization_id,
            action="security.mfa_recovery_regenerated",
            resource_type="user",
            resource_id=str(user.id),
            actor_user_id=user.id,
            details={"new_code_count": 10},
        )

        return MFARecoveryRegenerateResponse(recovery_codes=new_codes)

    def get_mfa_status(self, user: UserModel) -> MFAStatusResponse:
        """Return current MFA status metrics for user."""
        remaining = RecoveryService.get_remaining_count(user.mfa_backup_codes or "[]")
        return MFAStatusResponse(
            mfa_enabled=user.mfa_enabled,
            mfa_verified_at=(
                user.mfa_verified_at.isoformat() if user.mfa_verified_at else None
            ),
            mfa_last_used_at=(
                user.mfa_last_used_at.isoformat() if user.mfa_last_used_at else None
            ),
            backup_codes_remaining=remaining,
        )
