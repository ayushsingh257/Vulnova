"""Unit and Integration Tests for Security Audit Logging System."""

import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.api.v1.dependencies.auth import (
    get_current_active_user,
    get_current_user,
)
from app.api.v1.dependencies.client_info import get_client_info
from app.api.v1.routers.audit_logs import router as audit_logs_router
from app.application.audit_logs.dto import (
    AuditLogListResponse,
    AuditLogResponse,
)
from app.application.audit_logs.services import AuditLogService
from app.core.exceptions import ResourceNotFoundException, VulnovaException
from app.infrastructure.database.models.audit_log import AuditLogModel
from app.infrastructure.database.models.user import UserModel
from app.main import vulnova_exception_handler


def _make_mock_audit_log(
    log_id: Any = None,
    org_id: Any = None,
    actor_id: Any = None,
    action: str = "auth.login_success",
    resource_type: str = "user",
    resource_id: Any = None,
) -> AuditLogModel:
    log = MagicMock(spec=AuditLogModel)
    log.id = log_id or uuid4()
    log.organization_id = org_id or uuid4()
    log.actor_user_id = actor_id or uuid4()
    log.action = action
    log.resource_type = resource_type
    log.resource_id = str(resource_id or uuid4())
    log.client_ip = "192.168.1.10"
    log.user_agent = "Mozilla/5.0 TestAgent"
    log.details = {"status": "success"}
    log.created_at = MagicMock()
    return log


def _make_mock_user(org_id: Any = None, role: str = "ADMIN") -> UserModel:
    u = MagicMock(spec=UserModel)
    u.id = uuid4()
    u.organization_id = org_id or uuid4()
    u.email = "admin@example.com"
    u.full_name = "Admin User"
    u.role = role
    u.is_active = True
    return u


# ───────────────────────────────────────────────
# 1. AuditLogService Unit Tests
# ───────────────────────────────────────────────


def test_audit_service_record_event() -> None:
    """Test recording an audit log event."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = AuditLogService(mock_session)

            org_id = uuid4()
            actor_id = uuid4()
            mock_log = _make_mock_audit_log(org_id=org_id, actor_id=actor_id)

            mock_repo = AsyncMock()
            mock_repo.create.return_value = mock_log
            service.repo = mock_repo

            res = await service.record_event(
                organization_id=org_id,
                action="user.created",
                resource_type="user",
                resource_id=str(actor_id),
                actor_user_id=actor_id,
                client_ip="10.0.0.1",
                user_agent="TestRunner",
                details={"role": "ADMIN"},
            )

            assert res.organization_id == org_id
            assert res.action == "auth.login_success"
            mock_repo.create.assert_called_once()

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_audit_service_list_audit_logs() -> None:
    """Test listing audit logs with pagination and filters."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = AuditLogService(mock_session)

            org_id = uuid4()
            mock_log = _make_mock_audit_log(org_id=org_id)

            mock_repo = AsyncMock()
            mock_repo.list_by_organization.return_value = ([mock_log], 1)
            service.repo = mock_repo

            res = await service.list_audit_logs(
                organization_id=org_id,
                action="auth.login_success",
                resource_type="user",
                limit=10,
                offset=0,
            )

            assert res.total == 1
            assert res.limit == 10
            assert res.offset == 0
            assert len(res.audit_logs) == 1
            mock_repo.list_by_organization.assert_called_once_with(
                organization_id=org_id,
                action="auth.login_success",
                resource_type="user",
                actor_user_id=None,
                limit=10,
                offset=0,
            )

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_audit_service_get_detail_not_found() -> None:
    """Test getting audit log detail raises ResourceNotFoundException if absent."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = AuditLogService(mock_session)

            mock_repo = AsyncMock()
            mock_repo.get_by_id_and_org.return_value = None
            service.repo = mock_repo

            with pytest.raises(ResourceNotFoundException):
                await service.get_audit_log_detail(uuid4(), uuid4())

        loop.run_until_complete(_run())
    finally:
        loop.close()


# ───────────────────────────────────────────────
# 2. Client Info Context Dependency Tests
# ───────────────────────────────────────────────


def test_get_client_info_extraction() -> None:
    """Test client IP and User-Agent extraction from Request."""
    mock_req = MagicMock(spec=Request)
    mock_req.headers = {
        "x-forwarded-for": "203.0.113.195, 70.41.3.18",
        "user-agent": "VulnovaTestAgent/1.0",
    }
    mock_req.client = None

    ip, ua = get_client_info(mock_req)
    assert ip == "203.0.113.195"
    assert ua == "VulnovaTestAgent/1.0"


# ───────────────────────────────────────────────
# 3. FastAPI Endpoint Integration Tests
# ───────────────────────────────────────────────

audit_test_app = FastAPI()
audit_test_app.add_exception_handler(VulnovaException, vulnova_exception_handler)
audit_test_app.include_router(audit_logs_router)

test_org_id = uuid4()
mock_admin = _make_mock_user(org_id=test_org_id, role="ADMIN")


def _override_current_user() -> UserModel:
    return mock_admin


audit_test_app.dependency_overrides[get_current_user] = _override_current_user
audit_test_app.dependency_overrides[get_current_active_user] = _override_current_user


def test_list_audit_logs_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """GET /audit-logs returns paginated security audit events for ADMIN role."""
    log_id = uuid4()
    mock_service = AsyncMock()
    mock_service.list_audit_logs.return_value = {
        "audit_logs": [
            {
                "id": str(log_id),
                "organization_id": str(test_org_id),
                "actor_user_id": str(mock_admin.id),
                "action": "auth.login_success",
                "resource_type": "user",
                "resource_id": str(mock_admin.id),
                "client_ip": "127.0.0.1",
                "user_agent": "PytestClient",
                "details": {"status": "success"},
                "created_at": "2026-08-01T12:00:00Z",
            }
        ],
        "total": 1,
        "limit": 50,
        "offset": 0,
    }
    monkeypatch.setattr(
        "app.api.v1.routers.audit_logs.AuditLogService",
        lambda session: mock_service,
    )

    client = TestClient(audit_test_app)
    response = client.get("/audit-logs?limit=50&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["audit_logs"]) == 1
    assert data["audit_logs"][0]["id"] == str(log_id)


def test_get_audit_log_detail_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """GET /audit-logs/{audit_log_id} returns specific audit event details."""
    log_id = uuid4()
    mock_service = AsyncMock()
    mock_service.get_audit_log_detail.return_value = {
        "id": str(log_id),
        "organization_id": str(test_org_id),
        "actor_user_id": str(mock_admin.id),
        "action": "api_key.revoked",
        "resource_type": "api_key",
        "resource_id": str(uuid4()),
        "client_ip": "127.0.0.1",
        "user_agent": "PytestClient",
        "details": {"revoked": True},
        "created_at": "2026-08-01T12:00:00Z",
    }
    monkeypatch.setattr(
        "app.api.v1.routers.audit_logs.AuditLogService",
        lambda session: mock_service,
    )

    client = TestClient(audit_test_app)
    response = client.get(f"/audit-logs/{log_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(log_id)
    assert data["action"] == "api_key.revoked"
