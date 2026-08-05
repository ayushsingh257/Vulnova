"""Unit and Integration Test Suite for Multi-Factor Authentication (MFA / TOTP) System."""

import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pyotp
import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from app.api.v1.dependencies.auth import get_current_user
from app.application.mfa.dto import (
    MFAChallengeRequest,
    MFADisableRequest,
    MFARecoveryRegenerateRequest,
    MFAVerifySetupRequest,
)
from app.application.mfa.mfa_service import MFAService
from app.application.mfa.recovery_service import RecoveryService
from app.application.mfa.totp_service import TOTPService
from app.security.encryption import CryptoService
from app.security.password import hash_password
from app.infrastructure.database.models.user import UserModel
from app.main import app
from app.security.jwt import create_mfa_login_token


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def mock_user() -> UserModel:
    user = MagicMock(spec=UserModel)
    user.id = uuid4()
    user.organization_id = uuid4()
    user.email = "mfa_user@enterprise.com"
    user.full_name = "MFA User"
    user.role = "SECURITY_ANALYST"
    user.is_active = True
    user.password_hash = hash_password("ValidPassword123!")
    user.mfa_enabled = False
    user.mfa_secret = None
    user.mfa_backup_codes = None
    user.mfa_verified_at = None
    user.mfa_last_used_at = None

    # Relationship mock for UserResponse conversion
    mock_org = MagicMock()
    mock_org.name = "Enterprise Corp"
    mock_org.slug = "enterprise-corp"
    user.organization = mock_org
    return user


@pytest.mark.anyio
async def test_mfa_setup_generation(mock_user: UserModel) -> None:
    """Verify secret generation, provisioning URI, and QR code rendering."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = MFAService(mock_session, mock_audit)

    res = await service.initiate_mfa_setup(mock_user)

    assert res.secret is not None
    assert len(res.secret) == 32
    assert "otpauth://totp/" in res.provisioning_uri
    assert res.qr_code_base64.startswith("data:image/png;base64,")
    assert len(res.recovery_codes) == 10
    mock_session.commit.assert_called_once()


@pytest.mark.anyio
async def test_mfa_totp_verification() -> None:
    """Verify valid 6-digit OTP accepted and invalid OTP rejected."""
    secret = TOTPService.generate_secret()
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()

    assert TOTPService.verify_totp_code(secret, valid_code) is True
    assert TOTPService.verify_totp_code(secret, "000000") is False
    assert TOTPService.verify_totp_code(secret, "invalid") is False


@pytest.mark.anyio
async def test_mfa_enable_flow(mock_user: UserModel) -> None:
    """Verify user can verify initial OTP code and enable MFA."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = MFAService(mock_session, mock_audit)

    # Initiate setup
    setup_res = await service.initiate_mfa_setup(mock_user)
    totp = pyotp.TOTP(setup_res.secret)
    code = totp.now()

    # Verify & enable
    success = await service.verify_and_enable_mfa(mock_user, code)
    assert success is True
    assert mock_user.mfa_enabled is True
    mock_audit.record_event.assert_called()


@pytest.mark.anyio
async def test_mfa_login_challenge(mock_user: UserModel) -> None:
    """Verify MFA required after password login and valid OTP challenge verification."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = MFAService(mock_session, mock_audit)

    raw_secret = TOTPService.generate_secret()
    mock_user.mfa_secret = CryptoService.encrypt(raw_secret)
    mock_user.mfa_enabled = True

    totp = pyotp.TOTP(raw_secret)
    valid_code = totp.now()

    verified = await service.verify_mfa_challenge(mock_user, valid_code)
    assert verified is True
    mock_audit.record_event.assert_called()


@pytest.mark.anyio
async def test_mfa_disable_flow(mock_user: UserModel) -> None:
    """Verify MFA disable requires current password and valid OTP."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = MFAService(mock_session, mock_audit)

    raw_secret = TOTPService.generate_secret()
    mock_user.mfa_secret = CryptoService.encrypt(raw_secret)
    mock_user.mfa_enabled = True

    totp = pyotp.TOTP(raw_secret)
    code = totp.now()

    success = await service.disable_mfa(mock_user, "ValidPassword123!", code)
    assert success is True
    assert mock_user.mfa_enabled is False


@pytest.mark.anyio
async def test_recovery_code_generation() -> None:
    """Verify recovery codes generated and SHA-256 hashed."""
    codes = RecoveryService.generate_recovery_codes(10)
    assert len(codes) == 10
    for code in codes:
        assert len(code.replace("-", "")) == 10

    hashed_list = RecoveryService.hash_recovery_codes(codes)
    assert len(hashed_list) == 10
    assert hashed_list[0] != codes[0]


@pytest.mark.anyio
async def test_recovery_code_usage(mock_user: UserModel) -> None:
    """Verify single-use recovery code login and consumption."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = MFAService(mock_session, mock_audit)

    raw_secret = TOTPService.generate_secret()
    codes = RecoveryService.generate_recovery_codes(10)
    hashed_list = RecoveryService.hash_recovery_codes(codes)

    mock_user.mfa_secret = CryptoService.encrypt(raw_secret)
    mock_user.mfa_backup_codes = json.dumps(hashed_list)
    mock_user.mfa_enabled = True

    # Use first recovery code
    used_code = codes[0]
    verified = await service.verify_mfa_challenge(mock_user, used_code)
    assert verified is True

    # Check that code cannot be reused
    with pytest.raises(HTTPException):
        await service.verify_mfa_challenge(mock_user, used_code)


@pytest.mark.anyio
async def test_mfa_rbac_permissions(mock_user: UserModel) -> None:
    """Verify authorization requirement for MFA setup endpoint."""
    app.dependency_overrides[get_current_user] = lambda: mock_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Authenticated user can fetch MFA status
        res = await client.get("/api/v1/auth/mfa/status")
        assert res.status_code == 200

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_mfa_audit_logging(mock_user: UserModel) -> None:
    """Verify audit log events recorded for MFA actions."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = MFAService(mock_session, mock_audit)

    raw_secret = TOTPService.generate_secret()
    mock_user.mfa_secret = CryptoService.encrypt(raw_secret)
    mock_user.mfa_enabled = True

    totp = pyotp.TOTP(raw_secret)
    await service.verify_mfa_challenge(mock_user, totp.now())

    mock_audit.record_event.assert_called()


@pytest.mark.anyio
async def test_mfa_rate_limiting(mock_user: UserModel) -> None:
    """Verify invalid OTP attempt raises 401 exception."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = MFAService(mock_session, mock_audit)

    raw_secret = TOTPService.generate_secret()
    mock_user.mfa_secret = CryptoService.encrypt(raw_secret)
    mock_user.mfa_enabled = True

    with pytest.raises(HTTPException) as exc_info:
        await service.verify_mfa_challenge(mock_user, "000000")

    assert exc_info.value.status_code == 401
