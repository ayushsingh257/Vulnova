"""Unit and Integration Test Suite for Slack & Microsoft Teams Security Alert Webhooks."""

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.routers.notifications import get_notification_service
from app.application.notifications.dto import (
    CreateChannelRequest,
    SecurityNotificationEventDTO,
)
from app.application.notifications.notification_service import NotificationService
from app.application.notifications.providers.slack_provider import SlackWebhookProvider
from app.application.notifications.providers.teams_provider import TeamsWebhookProvider
from app.infrastructure.database.models.user import UserModel
from app.main import app
from app.security.encryption import SecretEncryptionService


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def mock_admin_user() -> UserModel:
    user = MagicMock(spec=UserModel)
    user.id = uuid4()
    user.organization_id = uuid4()
    user.email = "admin@enterprise.com"
    user.full_name = "Enterprise Admin"
    user.role = "ADMIN"
    user.is_active = True
    return user


@pytest.fixture
def mock_analyst_user(mock_admin_user: UserModel) -> UserModel:
    user = MagicMock(spec=UserModel)
    user.id = uuid4()
    user.organization_id = mock_admin_user.organization_id
    user.email = "analyst@enterprise.com"
    user.full_name = "Security Analyst"
    user.role = "SECURITY_ANALYST"
    user.is_active = True
    return user


@pytest.fixture
def mock_viewer_user(mock_admin_user: UserModel) -> UserModel:
    user = MagicMock(spec=UserModel)
    user.id = uuid4()
    user.organization_id = mock_admin_user.organization_id
    user.email = "viewer@enterprise.com"
    user.full_name = "Security Viewer"
    user.role = "VIEWER"
    user.is_active = True
    return user


def create_sample_event(
    event_type: str = "CRITICAL_FINDING_DISCOVERED", severity: str = "CRITICAL"
) -> SecurityNotificationEventDTO:
    return SecurityNotificationEventDTO(
        event_type=event_type,
        title="SQL Injection Vulnerability Discovered",
        description="Unsanitized user payload allows remote database extraction.",
        severity=severity,
        risk_score=9.8,
        target_asset="payments-api",
        finding_id=str(uuid4()),
        scan_id=str(uuid4()),
    )


@pytest.mark.anyio
async def test_slack_notification_delivery() -> None:
    """Verify Slack Block Kit payload structure and delivery handling."""
    provider = SlackWebhookProvider()
    event = create_sample_event()
    payload = provider.format_block_kit_payload(event)

    assert "attachments" in payload
    assert payload["attachments"][0]["color"] == "#DC2626"
    assert len(payload["attachments"][0]["blocks"]) >= 4

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_post.return_value = mock_res

        deliv = await provider.send_alert(
            channel_id="ch_slack_1",
            webhook_url="https://hooks.slack.com/services/T00/B00/X1",
            event=event,
        )
        assert deliv.status == "DELIVERED"
        assert deliv.status_code == 200


@pytest.mark.anyio
async def test_teams_notification_delivery() -> None:
    """Verify Microsoft Teams Adaptive Card payload structure and delivery handling."""
    provider = TeamsWebhookProvider()
    event = create_sample_event()
    payload = provider.format_adaptive_card_payload(event)

    assert payload["@type"] == "MessageCard"
    assert payload["themeColor"] == "DC2626"
    assert len(payload["sections"]) == 1
    assert payload["sections"][0]["facts"][0]["value"] == "CRITICAL"

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_res = MagicMock()
        mock_res.status_code = 200
        mock_post.return_value = mock_res

        deliv = await provider.send_alert(
            channel_id="ch_teams_1",
            webhook_url="https://outlook.office.com/webhook/X1",
            event=event,
        )
        assert deliv.status == "DELIVERED"
        assert deliv.status_code == 200


def test_webhook_secret_encryption() -> None:
    """Verify webhook secrets encryption using SecretEncryptionService."""
    enc = SecretEncryptionService()
    webhook_url = "https://hooks.slack.com/services/T123/B456/SECRET_TOKEN"
    encrypted = enc.encrypt_secret(webhook_url)

    assert encrypted != webhook_url
    assert enc.decrypt_secret(encrypted) == webhook_url


@pytest.mark.anyio
async def test_notification_tenant_isolation(mock_admin_user: UserModel) -> None:
    """Verify channel management is isolated per tenant organization."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = NotificationService(mock_session, mock_audit)

    req = CreateChannelRequest(
        provider="slack",
        name="#sec-alerts",
        webhook_url="https://hooks.slack.com/services/T00/B00/SEC",
        event_types=["CRITICAL_FINDING_DISCOVERED"],
        min_severity="CRITICAL",
    )
    ch = await service.create_channel(mock_admin_user, req)
    assert ch.name == "#sec-alerts"
    assert "SEC" in ch.webhook_url_masked or "hooks" in ch.webhook_url_masked

    channels = await service.list_channels(mock_admin_user)
    assert len(channels) == 1
    assert channels[0].id == ch.id

    # Different org user should see 0 channels
    other_org_user = MagicMock(spec=UserModel)
    other_org_user.organization_id = uuid4()
    other_channels = await service.list_channels(other_org_user)
    assert len(other_channels) == 0


@pytest.mark.anyio
async def test_notification_rbac_permissions(
    mock_admin_user: UserModel,
    mock_analyst_user: UserModel,
    mock_viewer_user: UserModel,
) -> None:
    """Verify RBAC permissions for notifications endpoints."""
    mock_service = AsyncMock()
    mock_service.list_channels.return_value = []

    app.dependency_overrides[get_notification_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = lambda: mock_viewer_user
    app.dependency_overrides[get_current_user_or_api_key] = lambda: mock_viewer_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Viewer can list channels
        res_list = await client.get("/api/v1/notifications/channels")
        assert res_list.status_code == 200

        # Viewer CANNOT create channel (requires ADMIN / notifications:manage)
        res_create = await client.post(
            "/api/v1/notifications/channels",
            json={
                "provider": "slack",
                "name": "#test",
                "webhook_url": "https://hooks.slack.com/services/1",
            },
        )
        assert res_create.status_code == 403

        # Switch to Admin
        app.dependency_overrides[get_current_user] = lambda: mock_admin_user
        app.dependency_overrides[get_current_user_or_api_key] = lambda: mock_admin_user
        mock_service.create_channel.return_value = {
            "id": "ch_1",
            "provider": "slack",
            "name": "#test",
            "webhook_url_masked": "https://hooks.slack.com/...",
            "event_types": [],
            "min_severity": "HIGH",
            "is_active": True,
            "created_at": "2026-08-05T00:00:00Z",
        }
        res_admin_create = await client.post(
            "/api/v1/notifications/channels",
            json={
                "provider": "slack",
                "name": "#test",
                "webhook_url": "https://hooks.slack.com/services/1",
            },
        )
        assert res_admin_create.status_code == 201

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_notification_audit_logging(mock_admin_user: UserModel) -> None:
    """Verify audit log events recorded for channel creation and deletion."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = NotificationService(mock_session, mock_audit)

    req = CreateChannelRequest(
        provider="teams",
        name="Security Team",
        webhook_url="https://outlook.office.com/webhook/123",
    )
    ch = await service.create_channel(mock_admin_user, req)
    mock_audit.record_event.assert_called()

    await service.delete_channel(mock_admin_user, ch.id)
    assert mock_audit.record_event.call_count >= 2


@pytest.mark.anyio
async def test_failed_delivery_handling(mock_admin_user: UserModel) -> None:
    """Verify HTTP failure or timeout does not raise unhandled exceptions."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = NotificationService(mock_session, mock_audit)

    req = CreateChannelRequest(
        provider="slack",
        name="#broken-hook",
        webhook_url="https://hooks.slack.com/services/BROKEN",
        min_severity="ALL",
    )
    ch = await service.create_channel(mock_admin_user, req)

    event = create_sample_event()

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_res = MagicMock()
        mock_res.status_code = 500
        mock_res.text = "Internal Server Error"
        mock_post.return_value = mock_res

        responses = await service.send_notification(
            mock_admin_user.organization_id, event
        )
        assert len(responses) == 1
        assert responses[0].status == "FAILED"
        assert responses[0].status_code == 500


@pytest.mark.anyio
async def test_notification_event_routing(mock_admin_user: UserModel) -> None:
    """Verify severity filters prevent dispatching low severity events when channel requires CRITICAL."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = NotificationService(mock_session, mock_audit)

    req = CreateChannelRequest(
        provider="slack",
        name="#critical-only",
        webhook_url="https://hooks.slack.com/services/CRITICAL",
        event_types=["MEDIUM_FINDING_DISCOVERED"],
        min_severity="CRITICAL",
    )
    await service.create_channel(mock_admin_user, req)

    medium_event = create_sample_event(
        event_type="MEDIUM_FINDING_DISCOVERED", severity="MEDIUM"
    )

    with patch("httpx.AsyncClient.post") as mock_post:
        responses = await service.send_notification(
            mock_admin_user.organization_id, medium_event
        )
        # Should filter out medium event and dispatch 0 notifications
        assert len(responses) == 0
        mock_post.assert_not_called()
