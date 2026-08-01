"""Phase 2.2 — JWT & OAuth2 Authentication Framework Test Suite."""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1.dependencies.auth import get_current_active_user
from app.application.auth.dto import RegisterRequest, TokenResponse, UserResponse
from app.application.auth.services import AuthService
from app.core.exceptions import UnauthorizedException, ValidationException
from app.infrastructure.database.models.organization import OrganizationModel
from app.infrastructure.database.models.refresh_token import RefreshTokenModel
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session
from app.main import app
from app.security.jwt import create_access_token, decode_access_token, hash_token
from app.security.password import hash_password, verify_password

client = TestClient(app)


async def _mock_async_session() -> AsyncGenerator[AsyncMock, None]:
    """Dependency override providing a mock AsyncSession generator."""
    yield AsyncMock()


# ───────────────────────────────────────────────
# 1. Password Hashing Tests (Argon2id)
# ───────────────────────────────────────────────


def test_argon2id_password_hashing() -> None:
    """Verify password hashing creates a valid Argon2id hash and verifies correctly."""
    plain = "SuperSecretP@ssword123!"
    hashed = hash_password(plain)

    assert hashed != plain
    assert hashed.startswith("$argon2id$")
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


# ───────────────────────────────────────────────
# 2. JWT Access Token Tests (HS256)
# ───────────────────────────────────────────────


def test_jwt_create_and_decode() -> None:
    """Verify JWT access token encoding, claims, and decoding."""
    user_id = uuid4()
    org_id = uuid4()
    role = "OWNER"

    token = create_access_token(
        user_id=user_id,
        organization_id=org_id,
        role=role,
    )
    assert isinstance(token, str)
    assert len(token) > 0

    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["user_id"] == str(user_id)
    assert payload["organization_id"] == str(org_id)
    assert payload["role"] == role
    assert payload["token_type"] == "access"


def test_jwt_expired_token_rejection() -> None:
    """Verify expired JWT tokens raise UnauthorizedException."""
    user_id = uuid4()
    org_id = uuid4()

    token = create_access_token(
        user_id=user_id,
        organization_id=org_id,
        role="SECURITY_ANALYST",
        expires_delta=timedelta(seconds=-10),  # Already expired
    )

    with pytest.raises(UnauthorizedException, match="Access token has expired"):
        decode_access_token(token)


def test_jwt_invalid_token_rejection() -> None:
    """Verify malformed tokens raise UnauthorizedException."""
    with pytest.raises(UnauthorizedException, match="Invalid access token"):
        decode_access_token("invalid.jwt.token.string")


# ───────────────────────────────────────────────
# 3. Token Cryptographic Hashing Tests
# ───────────────────────────────────────────────


def test_token_hash_deterministic() -> None:
    """Verify SHA-256 token hashing is deterministic and non-reversible."""
    raw = "sample_raw_refresh_token_string"
    h1 = hash_token(raw)
    h2 = hash_token(raw)

    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex digest length
    assert h1 != raw


# ───────────────────────────────────────────────
# 4. AuthService Unit & Rotation Engine Tests
# ───────────────────────────────────────────────


def test_auth_service_register_and_login() -> None:
    """Test AuthService register and login use cases with mock AsyncSession."""

    async def _async_test() -> None:
        mock_session = AsyncMock()

        org_store = {}
        user_store = {}
        token_store = {}

        async def mock_get_org_by_slug(slug: str):
            return org_store.get(slug)

        async def mock_get_user_by_email(email: str, load_organization: bool = False):
            user = user_store.get(email)
            if user and load_organization:
                user.organization = org_store.get("acme-sec")
            return user

        async def mock_get_user_by_id(user_id: UUID, load_organization: bool = False):
            for u in user_store.values():
                if u.id == user_id:
                    if load_organization:
                        u.organization = org_store.get("acme-sec")
                    return u
            return None

        async def mock_create_org(org: OrganizationModel):
            org_store[org.slug] = org
            return org

        async def mock_create_user(user: UserModel):
            user_store[user.email] = user
            return user

        async def mock_create_token(token: RefreshTokenModel):
            token_store[token.token_hash] = token
            return token

        async def mock_get_token_by_hash(token_hash: str):
            return token_store.get(token_hash)

        async def mock_revoke_family(family_id: UUID):
            for t in token_store.values():
                if t.family_id == family_id:
                    t.is_revoked = True

        async def mock_revoke_by_hash(token_hash: str):
            if token_hash in token_store:
                token_store[token_hash].is_revoked = True

        service = AuthService(mock_session)
        service.org_repo.get_by_slug = AsyncMock(side_effect=mock_get_org_by_slug)
        service.org_repo.create = AsyncMock(side_effect=mock_create_org)
        service.user_repo.get_by_email = AsyncMock(side_effect=mock_get_user_by_email)
        service.user_repo.get_by_id = AsyncMock(side_effect=mock_get_user_by_id)
        service.user_repo.create = AsyncMock(side_effect=mock_create_user)
        service.user_repo.update_last_login = AsyncMock()
        service.refresh_repo.create = AsyncMock(side_effect=mock_create_token)
        service.refresh_repo.get_by_hash = AsyncMock(side_effect=mock_get_token_by_hash)
        service.refresh_repo.revoke_family = AsyncMock(side_effect=mock_revoke_family)
        service.refresh_repo.revoke_by_hash = AsyncMock(side_effect=mock_revoke_by_hash)

        # 1. Register
        reg_req = RegisterRequest(
            email="owner@acme-sec.com",
            password="ComplexPassword123!",
            full_name="Alice Owner",
            organization_name="Acme Security",
            organization_slug="acme-sec",
        )
        user, org = await service.register(reg_req)
        assert user.email == "owner@acme-sec.com"
        assert user.role == "OWNER"
        assert org.slug == "acme-sec"

        # Duplicate registration raises ValidationException
        with pytest.raises(ValidationException, match="already taken"):
            await service.register(reg_req)

        # 2. Login
        token_resp, raw_refresh_token = await service.login(
            "owner@acme-sec.com", "ComplexPassword123!"
        )
        assert token_resp.access_token is not None
        assert raw_refresh_token is not None
        assert token_resp.user.email == "owner@acme-sec.com"

        # Wrong password raises UnauthorizedException
        with pytest.raises(UnauthorizedException, match="Invalid email or password"):
            await service.login("owner@acme-sec.com", "WrongPassword!")

        # 3. Refresh Token Rotation
        new_token_resp, new_raw_refresh_token = await service.refresh(raw_refresh_token)
        assert isinstance(new_token_resp.access_token, str)
        assert new_raw_refresh_token != raw_refresh_token

        # 4. Refresh Token REUSE DETECTION (Re-using old raw_refresh_token)
        with pytest.raises(UnauthorizedException, match="reuse detected"):
            await service.refresh(raw_refresh_token)

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_async_test())
    finally:
        loop.close()


# ───────────────────────────────────────────────
# 5. Auth API Router Endpoints Tests
# ───────────────────────────────────────────────


@patch.object(AuthService, "register")
def test_api_register_endpoint(mock_register: AsyncMock) -> None:
    """Test POST /api/v1/auth/register endpoint."""
    app.dependency_overrides[get_async_session] = _mock_async_session

    try:
        org_id = uuid4()
        user_id = uuid4()
        now = datetime.now(timezone.utc)

        dummy_user = MagicMock(spec=UserModel)
        dummy_user.id = user_id
        dummy_user.organization_id = org_id
        dummy_user.email = "owner@acme.com"
        dummy_user.full_name = "Alice Admin"
        dummy_user.role = "OWNER"
        dummy_user.is_active = True
        dummy_user.is_mfa_enabled = False
        dummy_user.created_at = now

        dummy_org = MagicMock(spec=OrganizationModel)
        dummy_org.id = org_id
        dummy_org.name = "Acme Security"
        dummy_org.slug = "acme-sec"
        dummy_org.plan_tier = "ENTERPRISE_TRIAL"
        dummy_org.is_active = True
        dummy_org.created_at = now

        mock_register.return_value = (dummy_user, dummy_org)

        payload = {
            "email": "owner@acme.com",
            "password": "Password123!",
            "full_name": "Alice Admin",
            "organization_name": "Acme Security",
            "organization_slug": "acme-sec",
        }
        res = client.post("/api/v1/auth/register", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["email"] == "owner@acme.com"
        assert data["role"] == "OWNER"
    finally:
        app.dependency_overrides.clear()


@patch.object(AuthService, "login")
def test_api_login_endpoint(mock_login: AsyncMock) -> None:
    """Test POST /api/v1/auth/login endpoint."""
    app.dependency_overrides[get_async_session] = _mock_async_session

    try:
        org_id = uuid4()
        user_id = uuid4()
        now = datetime.now(timezone.utc)

        user_resp = UserResponse(
            id=user_id,
            organization_id=org_id,
            organization_name="Acme Sec",
            organization_slug="acme-sec",
            email="owner@acme.com",
            full_name="Alice Admin",
            role="OWNER",
            is_active=True,
            is_mfa_enabled=False,
            created_at=now,
        )
        token_resp = TokenResponse(
            access_token="mock_access_token_jwt",
            token_type="bearer",
            user=user_resp,
        )
        mock_login.return_value = (token_resp, "mock_raw_refresh_token")

        res = client.post(
            "/api/v1/auth/login",
            json={"email": "owner@acme.com", "password": "Password123!"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["access_token"] == "mock_access_token_jwt"
        assert "vulnova_refresh_token" in res.cookies
    finally:
        app.dependency_overrides.clear()


@patch.object(AuthService, "refresh")
def test_api_refresh_endpoint(mock_refresh: AsyncMock) -> None:
    """Test POST /api/v1/auth/refresh endpoint."""
    app.dependency_overrides[get_async_session] = _mock_async_session

    try:
        org_id = uuid4()
        user_id = uuid4()
        now = datetime.now(timezone.utc)

        user_resp = UserResponse(
            id=user_id,
            organization_id=org_id,
            organization_name="Acme Sec",
            organization_slug="acme-sec",
            email="owner@acme.com",
            full_name="Alice Admin",
            role="OWNER",
            is_active=True,
            is_mfa_enabled=False,
            created_at=now,
        )
        token_resp = TokenResponse(
            access_token="new_mock_access_token_jwt",
            token_type="bearer",
            user=user_resp,
        )
        mock_refresh.return_value = (token_resp, "new_mock_raw_refresh_token")

        res = client.post(
            "/api/v1/auth/refresh",
            cookies={"vulnova_refresh_token": "valid_old_cookie_token"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["access_token"] == "new_mock_access_token_jwt"
        assert res.cookies["vulnova_refresh_token"] == "new_mock_raw_refresh_token"
    finally:
        app.dependency_overrides.clear()


@patch.object(AuthService, "logout")
def test_api_logout_endpoint(mock_logout: AsyncMock) -> None:
    """Test POST /api/v1/auth/logout endpoint."""
    app.dependency_overrides[get_async_session] = _mock_async_session

    try:
        mock_logout.return_value = None
        res = client.post(
            "/api/v1/auth/logout",
            cookies={"vulnova_refresh_token": "cookie_token_to_logout"},
        )
        assert res.status_code == 200
        assert res.json()["message"] == "Logged out successfully"
    finally:
        app.dependency_overrides.clear()


def test_api_get_me_endpoint_authenticated() -> None:
    """Test GET /api/v1/auth/me with valid Bearer token."""
    org_id = uuid4()
    user_id = uuid4()

    mock_user = MagicMock(spec=UserModel)
    mock_user.id = user_id
    mock_user.organization_id = org_id
    mock_user.email = "analyst@vulnova.com"
    mock_user.full_name = "Bob Analyst"
    mock_user.role = "SECURITY_ANALYST"
    mock_user.is_active = True
    mock_user.is_mfa_enabled = False
    mock_user.created_at = datetime.now(timezone.utc)

    mock_org = MagicMock(spec=OrganizationModel)
    mock_org.name = "Vulnova Sec"
    mock_org.slug = "vulnova-sec"
    mock_user.organization = mock_org

    app.dependency_overrides[get_current_active_user] = lambda: mock_user

    try:
        res = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer mock_valid_jwt_token"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["email"] == "analyst@vulnova.com"
        assert data["organization_slug"] == "vulnova-sec"
    finally:
        app.dependency_overrides.clear()


def test_api_get_me_endpoint_unauthenticated() -> None:
    """Test GET /api/v1/auth/me without token returns 401."""
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
