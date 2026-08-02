"""Unit and Integration Tests for User Management Services and API Endpoints."""

import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.dependencies.auth import get_current_active_user
from app.api.v1.routers.users import router as users_router
from app.application.users.dto import (
    InviteUserRequest,
    UpdateUserProfileRequest,
    UpdateUserRoleRequest,
    UpdateUserStatusRequest,
)
from app.application.users.services import UserService
from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    ResourceNotFoundException,
    ValidationException,
    VulnovaException,
)
from app.domain.entities.role import Role
from app.infrastructure.database.models.user import UserModel
from app.main import vulnova_exception_handler


def _make_mock_user(
    user_id: Any = None,
    org_id: Any = None,
    email: str = "test@example.com",
    role: str = "ADMIN",
    is_active: bool = True,
) -> UserModel:
    u = MagicMock(spec=UserModel)
    u.id = user_id or uuid4()
    u.organization_id = org_id or uuid4()
    u.email = email
    u.full_name = "Test User"
    u.role = role
    u.is_active = is_active
    u.is_mfa_enabled = False
    u.last_login_at = None
    u.created_at = MagicMock()
    return u


# ───────────────────────────────────────────────
# 1. UserService Unit Tests
# ───────────────────────────────────────────────


def test_user_service_update_profile() -> None:
    """Test updating authenticated user's profile."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = UserService(mock_session)

            user = _make_mock_user(email="alice@example.com")

            mock_repo = AsyncMock()
            mock_repo.update.return_value = user
            service.user_repo = mock_repo

            req = UpdateUserProfileRequest(full_name="Alice Smith")
            res = await service.update_profile(user, req)

            assert user.full_name == "Alice Smith"
            assert res.email == "alice@example.com"
            mock_repo.update.assert_called_once_with(user)

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_user_service_invite_user_duplicate_email() -> None:
    """Test inviting a user with an already existing email raises ConflictException."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = UserService(mock_session)

            caller = _make_mock_user(role="ADMIN")

            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = _make_mock_user(
                email="duplicate@example.com"
            )
            service.user_repo = mock_repo

            req = InviteUserRequest(
                email="duplicate@example.com",
                full_name="Dup User",
                password="password123",
                role="SECURITY_ANALYST",
            )

            with pytest.raises(ConflictException):
                await service.invite_user(req, caller)

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_user_service_non_owner_cannot_assign_owner_role() -> None:
    """Test non-OWNER user attempting to create an OWNER raises ForbiddenException."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = UserService(mock_session)

            caller = _make_mock_user(role="ADMIN")

            mock_repo = AsyncMock()
            mock_repo.get_by_email.return_value = None
            service.user_repo = mock_repo

            req = InviteUserRequest(
                email="newowner@example.com",
                full_name="New Owner",
                password="password123",
                role="OWNER",
            )

            with pytest.raises(ForbiddenException):
                await service.invite_user(req, caller)

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_user_service_update_role_sole_owner_protection() -> None:
    """Test demoting the sole active OWNER raises ValidationException."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = UserService(mock_session)

            org_id = uuid4()
            target_owner = _make_mock_user(org_id=org_id, role="OWNER")

            mock_repo = AsyncMock()
            mock_repo.get_by_id_and_org.return_value = target_owner
            mock_repo.count_owners_in_org.return_value = 1
            service.user_repo = mock_repo

            req = UpdateUserRoleRequest(role="ADMIN")

            with pytest.raises(ValidationException) as exc_info:
                await service.update_user_role(
                    target_owner.id, req, current_user=target_owner
                )

            assert "sole active OWNER" in str(exc_info.value)

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_user_service_self_deactivation_prevention() -> None:
    """Test users cannot deactivate their own account."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = UserService(mock_session)

            caller = _make_mock_user(role="ADMIN")

            req = UpdateUserStatusRequest(is_active=False)

            with pytest.raises(ValidationException) as exc_info:
                await service.update_user_status(
                    target_user_id=caller.id, req=req, current_user=caller
                )

            assert "cannot deactivate their own account" in str(exc_info.value)

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_user_service_self_deletion_prevention() -> None:
    """Test users cannot remove their own account."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = UserService(mock_session)

            caller = _make_mock_user(role="ADMIN")

            with pytest.raises(ValidationException) as exc_info:
                await service.remove_user(target_user_id=caller.id, current_user=caller)

            assert "cannot remove their own account" in str(exc_info.value)

        loop.run_until_complete(_run())
    finally:
        loop.close()


# ───────────────────────────────────────────────
# 2. FastAPI Endpoint Integration Tests
# ───────────────────────────────────────────────
from app.api.v1.dependencies.auth import (
    get_current_active_user,
    get_current_user,
)

user_test_app = FastAPI()
user_test_app.add_exception_handler(VulnovaException, vulnova_exception_handler)
user_test_app.include_router(users_router)

test_org_id = uuid4()
test_user_id = uuid4()
mock_active_user = _make_mock_user(
    user_id=test_user_id, org_id=test_org_id, role="OWNER"
)


def _override_current_user() -> UserModel:
    return mock_active_user


user_test_app.dependency_overrides[get_current_user] = _override_current_user
user_test_app.dependency_overrides[get_current_active_user] = _override_current_user


def test_get_my_profile_endpoint() -> None:
    """GET /users/me returns authenticated user's profile."""
    client = TestClient(user_test_app)
    response = client.get("/users/me")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_user_id)
    assert data["email"] == "test@example.com"
    assert data["role"] == "OWNER"


def test_update_my_profile_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """PATCH /users/me updates authenticated user's full name."""
    mock_service = AsyncMock()
    mock_service.update_profile.return_value = {
        "id": str(test_user_id),
        "organization_id": str(test_org_id),
        "email": "test@example.com",
        "full_name": "Updated Name",
        "role": "OWNER",
        "is_active": True,
        "is_mfa_enabled": False,
        "last_login_at": None,
        "created_at": "2026-08-01T12:00:00Z",
    }
    monkeypatch.setattr(
        "app.api.v1.routers.users.UserService", lambda session: mock_service
    )

    client = TestClient(user_test_app)
    response = client.patch("/users/me", json={"full_name": "Updated Name"})
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Updated Name"


def test_list_users_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """GET /users lists organization users when authenticated."""
    mock_service = AsyncMock()
    mock_service.list_organization_users.return_value = {
        "users": [
            {
                "id": str(test_user_id),
                "organization_id": str(test_org_id),
                "email": "test@example.com",
                "full_name": "Test User",
                "role": "OWNER",
                "is_active": True,
                "is_mfa_enabled": False,
                "last_login_at": None,
                "created_at": "2026-08-01T12:00:00Z",
            }
        ],
        "total": 1,
    }
    monkeypatch.setattr(
        "app.api.v1.routers.users.UserService", lambda session: mock_service
    )

    client = TestClient(user_test_app)
    response = client.get("/users")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["users"]) == 1


def test_create_user_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """POST /users invites a new team member."""
    new_id = uuid4()
    mock_service = AsyncMock()
    mock_service.invite_user.return_value = {
        "id": str(new_id),
        "organization_id": str(test_org_id),
        "email": "analyst@example.com",
        "full_name": "Analyst User",
        "role": "SECURITY_ANALYST",
        "is_active": True,
        "is_mfa_enabled": False,
        "last_login_at": None,
        "created_at": "2026-08-01T12:00:00Z",
    }
    monkeypatch.setattr(
        "app.api.v1.routers.users.UserService", lambda session: mock_service
    )

    client = TestClient(user_test_app)
    payload = {
        "email": "analyst@example.com",
        "full_name": "Analyst User",
        "password": "SecurePassword123!",
        "role": "SECURITY_ANALYST",
    }
    response = client.post("/users", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] == str(new_id)
    assert data["role"] == "SECURITY_ANALYST"


def test_delete_user_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """DELETE /users/{user_id} removes a user."""
    target_id = uuid4()
    mock_service = AsyncMock()
    mock_service.remove_user.return_value = None
    monkeypatch.setattr(
        "app.api.v1.routers.users.UserService", lambda session: mock_service
    )

    client = TestClient(user_test_app)
    response = client.delete(f"/users/{target_id}")
    assert response.status_code == 200
    assert response.json() == {"message": "User removed successfully"}
