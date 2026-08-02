"""Unit and Integration Tests for Organization Management Services and API Endpoints."""

import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.dependencies.auth import get_current_active_user
from app.api.v1.routers.organizations import router as orgs_router
from app.application.organizations.dto import (
    OrganizationDetailResponse,
    UpdateOrganizationRequest,
)
from app.application.organizations.services import OrganizationService
from app.core.exceptions import ResourceNotFoundException, VulnovaException
from app.infrastructure.database.models.organization import OrganizationModel
from app.infrastructure.database.models.user import UserModel
from app.main import vulnova_exception_handler


def _make_mock_org(
    org_id: Any = None,
    name: str = "Acme Security Corp",
    slug: str = "acme-sec",
    plan_tier: str = "ENTERPRISE_TRIAL",
    is_active: bool = True,
) -> OrganizationModel:
    o = MagicMock(spec=OrganizationModel)
    o.id = org_id or uuid4()
    o.name = name
    o.slug = slug
    o.plan_tier = plan_tier
    o.is_active = is_active
    o.created_at = MagicMock()
    o.updated_at = MagicMock()
    return o


def _make_mock_user(org_id: Any = None, role: str = "OWNER") -> UserModel:
    u = MagicMock(spec=UserModel)
    u.id = uuid4()
    u.organization_id = org_id or uuid4()
    u.email = "owner@example.com"
    u.full_name = "Owner User"
    u.role = role
    u.is_active = True
    return u


# ───────────────────────────────────────────────
# 1. OrganizationService Unit Tests
# ───────────────────────────────────────────────


def test_org_service_get_organization_success() -> None:
    """Test getting organization profile and member count."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = OrganizationService(mock_session)

            org_id = uuid4()
            mock_org = _make_mock_org(org_id=org_id)

            mock_repo = AsyncMock()
            mock_repo.get_with_member_count.return_value = (mock_org, 5)
            service.org_repo = mock_repo

            res = await service.get_organization(org_id)

            assert res.id == org_id
            assert res.name == "Acme Security Corp"
            assert res.member_count == 5
            mock_repo.get_with_member_count.assert_called_once_with(org_id)

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_org_service_get_organization_not_found() -> None:
    """Test fetching non-existent organization raises ResourceNotFoundException."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = OrganizationService(mock_session)

            mock_repo = AsyncMock()
            mock_repo.get_with_member_count.return_value = (None, 0)
            service.org_repo = mock_repo

            with pytest.raises(ResourceNotFoundException):
                await service.get_organization(uuid4())

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_org_service_update_organization() -> None:
    """Test updating organization settings."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = OrganizationService(mock_session)

            org_id = uuid4()
            mock_org = _make_mock_org(org_id=org_id)
            caller = _make_mock_user(org_id=org_id)

            mock_repo = AsyncMock()
            mock_repo.get_with_member_count.return_value = (mock_org, 3)
            mock_repo.update.return_value = mock_org
            service.org_repo = mock_repo

            req = UpdateOrganizationRequest(
                name="Acme Enterprise", plan_tier="ENTERPRISE_PRO"
            )
            res = await service.update_organization(org_id, req, caller)

            assert mock_org.name == "Acme Enterprise"
            assert mock_org.plan_tier == "ENTERPRISE_PRO"
            assert res.name == "Acme Enterprise"
            assert res.plan_tier == "ENTERPRISE_PRO"

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_org_service_deactivate_organization() -> None:
    """Test deactivating an organization."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = OrganizationService(mock_session)

            org_id = uuid4()
            mock_org = _make_mock_org(org_id=org_id)
            caller = _make_mock_user(org_id=org_id)

            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = mock_org
            mock_repo.update.return_value = mock_org
            service.org_repo = mock_repo

            await service.deactivate_organization(org_id, caller)

            assert mock_org.is_active is False
            mock_repo.update.assert_called_once_with(mock_org)

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

org_test_app = FastAPI()
org_test_app.add_exception_handler(VulnovaException, vulnova_exception_handler)
org_test_app.include_router(orgs_router)

test_org_id = uuid4()
mock_owner = _make_mock_user(org_id=test_org_id, role="OWNER")


def _override_current_user() -> UserModel:
    return mock_owner


org_test_app.dependency_overrides[get_current_user] = _override_current_user
org_test_app.dependency_overrides[get_current_active_user] = _override_current_user


def test_get_my_organization_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """GET /organizations/me returns organization profile and member count."""
    mock_service = AsyncMock()
    mock_service.get_organization.return_value = {
        "id": str(test_org_id),
        "name": "Acme Security Corp",
        "slug": "acme-sec",
        "plan_tier": "ENTERPRISE_TRIAL",
        "is_active": True,
        "created_at": "2026-08-01T12:00:00Z",
        "updated_at": "2026-08-01T12:00:00Z",
        "member_count": 4,
    }
    monkeypatch.setattr(
        "app.api.v1.routers.organizations.OrganizationService",
        lambda session: mock_service,
    )

    client = TestClient(org_test_app)
    response = client.get("/organizations/me")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_org_id)
    assert data["member_count"] == 4


def test_update_my_organization_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """PATCH /organizations/me updates organization settings."""
    mock_service = AsyncMock()
    mock_service.update_organization.return_value = {
        "id": str(test_org_id),
        "name": "Acme Global",
        "slug": "acme-sec",
        "plan_tier": "ENTERPRISE_PRO",
        "is_active": True,
        "created_at": "2026-08-01T12:00:00Z",
        "updated_at": "2026-08-01T12:00:00Z",
        "member_count": 4,
    }
    monkeypatch.setattr(
        "app.api.v1.routers.organizations.OrganizationService",
        lambda session: mock_service,
    )

    client = TestClient(org_test_app)
    payload = {"name": "Acme Global", "plan_tier": "ENTERPRISE_PRO"}
    response = client.patch("/organizations/me", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Acme Global"
    assert data["plan_tier"] == "ENTERPRISE_PRO"


def test_deactivate_my_organization_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """DELETE /organizations/me deactivates the organization."""
    mock_service = AsyncMock()
    mock_service.deactivate_organization.return_value = None
    monkeypatch.setattr(
        "app.api.v1.routers.organizations.OrganizationService",
        lambda session: mock_service,
    )

    client = TestClient(org_test_app)
    response = client.delete("/organizations/me")
    assert response.status_code == 200
    assert response.json() == {"message": "Organization deactivated successfully"}
