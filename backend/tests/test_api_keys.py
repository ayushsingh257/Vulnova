"""Test Suite for API Key Management System & Dual-Mode Authentication."""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI, status
from fastapi.testclient import TestClient

from app.api.v1.dependencies.api_key import (
    get_api_key_user,
    get_current_user_or_api_key,
)
from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.dependencies.rbac import require_permission
from app.application.api_keys.dto import CreateAPIKeyRequest
from app.application.api_keys.services import APIKeyService
from app.core.exceptions import (
    ResourceNotFoundException,
    UnauthorizedException,
    VulnovaException,
)
from app.infrastructure.database.models.api_key import APIKeyModel
from app.infrastructure.database.models.organization import OrganizationModel
from app.infrastructure.database.models.user import UserModel
from app.main import vulnova_exception_handler
from app.security.api_key import (
    API_KEY_PREFIX,
    PREFIX_LENGTH,
    generate_api_key,
    hash_api_key,
    verify_api_key,
)

# ───────────────────────────────────────────────
# 1. Security Unit Tests: Hashing & Format
# ───────────────────────────────────────────────


def test_generate_api_key_format_and_uniqueness() -> None:
    """Verify generated API key format, prefix, SHA-256 hash length, and uniqueness."""
    raw1, prefix1, hash1 = generate_api_key()
    raw2, prefix2, hash2 = generate_api_key()

    assert raw1 != raw2
    assert hash1 != hash2

    assert raw1.startswith(API_KEY_PREFIX)
    assert prefix1 == API_KEY_PREFIX
    assert len(prefix1) == PREFIX_LENGTH

    # Raw key must NOT be equal to its SHA-256 hash
    assert raw1 != hash1
    assert len(hash1) == 64  # SHA-256 hex digest length


def test_verify_api_key_constant_time() -> None:
    """Verify verify_api_key matching behavior."""
    raw_key, prefix, key_hash = generate_api_key()

    # Valid key matches
    assert verify_api_key(raw_key, key_hash) is True

    # Tampered key fails
    tampered_key = raw_key[:-1] + "X"
    assert verify_api_key(tampered_key, key_hash) is False


# ───────────────────────────────────────────────
# 2. Application Service Tests
# ───────────────────────────────────────────────


def test_api_key_service_lifecycle() -> None:
    """Test APIKeyService create, authenticate, list, expire, and revoke use cases."""
    mock_session = AsyncMock()
    org_id = uuid4()
    user_id = uuid4()

    mock_org = MagicMock(spec=OrganizationModel)
    mock_org.id = org_id
    mock_org.is_active = True

    mock_user = MagicMock(spec=UserModel)
    mock_user.id = user_id
    mock_user.organization_id = org_id
    mock_user.is_active = True
    mock_user.role = "ADMIN"

    key_store = {}

    async def mock_create(key: APIKeyModel):
        key_store[key.key_hash] = key
        return key

    async def mock_get_by_hash(key_hash: str, load_relationships: bool = True):
        key = key_store.get(key_hash)
        if key:
            key.__dict__["user"] = mock_user
            key.__dict__["organization"] = mock_org
        return key

    async def mock_list(organization_id):
        return [k for k in key_store.values() if k.organization_id == organization_id]

    async def mock_delete(key_id, organization_id):
        for h, k in list(key_store.items()):
            if k.id == key_id and k.organization_id == organization_id:
                del key_store[h]
                return True
        return False

    service = APIKeyService(mock_session)
    service.repo.create = AsyncMock(side_effect=mock_create)
    service.repo.get_by_hash = AsyncMock(side_effect=mock_get_by_hash)
    service.repo.list_by_organization = AsyncMock(side_effect=mock_list)
    service.repo.delete = AsyncMock(side_effect=mock_delete)
    service.repo.update_last_used = AsyncMock()

    loop = asyncio.new_event_loop()
    try:

        async def _run():
            # 1. Create API Key
            req = CreateAPIKeyRequest(
                name="CI Integration Key",
                scopes=["read", "write"],
                expires_in_days=30,
            )
            create_resp = await service.create_api_key(req, mock_user)

            assert create_resp.name == "CI Integration Key"
            assert create_resp.raw_key.startswith(API_KEY_PREFIX)
            assert create_resp.key_prefix == API_KEY_PREFIX

            # Verify raw key is NOT stored as key_hash
            stored_hash = hash_api_key(create_resp.raw_key)
            assert stored_hash in key_store
            assert key_store[stored_hash].key_hash != create_resp.raw_key

            # 2. Authenticate API Key
            key_model, auth_user = await service.authenticate_api_key(
                create_resp.raw_key
            )
            assert auth_user.id == user_id
            assert key_model.id == create_resp.id

            # 3. List API Keys
            keys_list = await service.list_api_keys(org_id)
            assert len(keys_list) == 1
            assert keys_list[0].id == create_resp.id

            # 4. Invalid key rejection
            with pytest.raises(UnauthorizedException, match="Invalid or revoked"):
                await service.authenticate_api_key(API_KEY_PREFIX + "invalidsecret123")

            # 5. Too short / bad format key rejection
            with pytest.raises(UnauthorizedException, match="Invalid API key format"):
                await service.authenticate_api_key("short")

            # 6. Expired key rejection
            expired_key = key_store[stored_hash]
            expired_key.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
            with pytest.raises(UnauthorizedException, match="expired"):
                await service.authenticate_api_key(create_resp.raw_key)
            expired_key.expires_at = datetime.now(timezone.utc) + timedelta(days=30)

            # 7. Inactive user rejection
            mock_user.is_active = False
            with pytest.raises(UnauthorizedException, match="User account"):
                await service.authenticate_api_key(create_resp.raw_key)
            mock_user.is_active = True

            # 8. Revoke API Key
            await service.revoke_api_key(create_resp.id, org_id, user_id)
            assert len(await service.list_api_keys(org_id)) == 0

            # 9. Revoking non-existent / cross-org key raises ResourceNotFoundException
            with pytest.raises(ResourceNotFoundException):
                await service.revoke_api_key(uuid4(), org_id, user_id)

        loop.run_until_complete(_run())
    finally:
        loop.close()


# ───────────────────────────────────────────────
# 3. Dual-Mode & Endpoint Integration Tests
# ───────────────────────────────────────────────

api_key_test_app = FastAPI()
api_key_test_app.add_exception_handler(VulnovaException, vulnova_exception_handler)

test_org_id = uuid4()
test_user_id = uuid4()


from typing import Any, Dict


@api_key_test_app.get("/test/protected-dual-mode")
async def dual_mode_protected_endpoint(
    user: UserModel = Depends(get_current_user_or_api_key),
) -> Dict[str, Any]:
    return {"message": "auth success", "user_id": str(user.id)}


@api_key_test_app.get("/test/protected-api-key-only")
async def api_key_only_endpoint(
    user: UserModel = Depends(get_api_key_user),
) -> Dict[str, Any]:
    return {"message": "api key success", "user_id": str(user.id)}


def _make_auth_user() -> UserModel:
    u = MagicMock(spec=UserModel)
    u.id = test_user_id
    u.organization_id = test_org_id
    u.role = "ADMIN"
    u.is_active = True
    return u


def test_dual_mode_auth_priority_and_fallback() -> None:
    """Test get_current_user_or_api_key prioritizing JWT Bearer over X-API-Key and falling back cleanly."""
    from app.security.jwt import create_access_token

    mock_jwt_user = _make_auth_user()
    mock_api_key_user = _make_auth_user()
    mock_api_key_user.id = uuid4()

    valid_jwt = create_access_token(
        user_id=mock_jwt_user.id,
        organization_id=mock_jwt_user.organization_id,
        role="ADMIN",
    )

    mock_user_repo = AsyncMock()
    mock_user_repo.get_by_id = AsyncMock(return_value=mock_jwt_user)

    mock_service_instance = AsyncMock()

    mock_secret_key = f"{API_KEY_PREFIX}mock_test_secret_value_12345"  # gitleaks:allow

    async def mock_auth_key(raw_key: str):
        if raw_key == mock_secret_key:
            return MagicMock(), mock_api_key_user
        raise UnauthorizedException("Invalid or revoked API key")

    mock_service_instance.authenticate_api_key = AsyncMock(side_effect=mock_auth_key)

    client = TestClient(api_key_test_app)
    try:
        with pytest.MonkeyPatch().context() as m:
            m.setattr(
                "app.api.v1.dependencies.auth.UserRepository",
                lambda session: mock_user_repo,
            )
            m.setattr(
                "app.api.v1.dependencies.api_key.APIKeyService",
                lambda session: mock_service_instance,
            )

            # 1. Bearer JWT only -> Authenticates via JWT
            res = client.get(
                "/test/protected-dual-mode",
                headers={"Authorization": f"Bearer {valid_jwt}"},
            )
            assert res.status_code == 200
            assert res.json()["user_id"] == str(mock_jwt_user.id)

            # 2. X-API-Key header only -> Authenticates via X-API-Key
            res = client.get(
                "/test/protected-dual-mode",
                headers={"X-API-Key": mock_secret_key},
            )
            assert res.status_code == 200
            assert res.json()["user_id"] == str(mock_api_key_user.id)

            # 3. Both headers present -> Prefers JWT Bearer
            res = client.get(
                "/test/protected-dual-mode",
                headers={
                    "Authorization": f"Bearer {valid_jwt}",
                    "X-API-Key": mock_secret_key,
                },
            )
            assert res.status_code == 200
            assert res.json()["user_id"] == str(mock_jwt_user.id)

        # 4. Neither header present -> 401 Unauthorized
        res = client.get("/test/protected-dual-mode")
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "UNAUTHORIZED"

    finally:
        api_key_test_app.dependency_overrides.clear()
