"""Data Transfer Objects (DTOs) for Multi-Factor Authentication (MFA / TOTP)."""

from typing import List, Optional

from pydantic import BaseModel, Field


class MFASetupResponse(BaseModel):
    """Response DTO for MFA setup initialization containing TOTP secret, provisioning URI, and QR code."""

    secret: str = Field(
        ..., description="Unencrypted base32 TOTP secret key for manual entry"
    )
    provisioning_uri: str = Field(
        ..., description="Standard otpauth:// URI for authenticator apps"
    )
    qr_code_base64: str = Field(
        ..., description="Base64-encoded PNG image string of QR code"
    )
    recovery_codes: List[str] = Field(
        ..., description="10 single-use plaintext recovery codes (save immediately)"
    )


class MFAVerifySetupRequest(BaseModel):
    """Request DTO to verify initial 6-digit OTP code and activate MFA."""

    code: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="6-digit OTP from authenticator app",
    )


class MFADisableRequest(BaseModel):
    """Request DTO to disable MFA requiring current password and valid OTP."""

    current_password: str = Field(..., description="Current account password")
    code: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")


class MFAChallengeRequest(BaseModel):
    """Request DTO for OTP verification during MFA login challenge or recovery code login."""

    mfa_login_token: str = Field(
        ...,
        description="Ephemeral MFA challenge token received after password verification",
    )
    code: str = Field(
        ..., description="6-digit TOTP code OR 10-character recovery code"
    )


class MFAStatusResponse(BaseModel):
    """Response DTO displaying MFA configuration and usage status."""

    mfa_enabled: bool = Field(..., description="Whether MFA is enabled on this account")
    mfa_verified_at: Optional[str] = Field(
        default=None, description="ISO timestamp when MFA was enabled"
    )
    mfa_last_used_at: Optional[str] = Field(
        default=None, description="ISO timestamp of last successful OTP verification"
    )
    backup_codes_remaining: int = Field(
        ..., description="Number of active, unused recovery codes remaining"
    )


class MFARecoveryRegenerateRequest(BaseModel):
    """Request DTO to regenerate new backup recovery codes."""

    current_password: str = Field(..., description="Current user account password")
    code: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")


class MFARecoveryRegenerateResponse(BaseModel):
    """Response DTO returning newly generated backup recovery codes."""

    recovery_codes: List[str] = Field(
        ..., description="List of 10 new plaintext single-use recovery codes"
    )
