"""Comprehensive test suite for Era 6 Phase 6.4 Real-Time Scan Progress & WebSocket Event Stream."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.application.assessment.scan_event_publisher import (
    ScanEventPublisherService,
)
from app.application.assessment.scan_stream_manager import (
    MAX_CONNECTIONS_PER_ORG,
    ScanStreamManagerService,
)
from app.core.exceptions import ForbiddenException
from app.domain.entities.assessment import Finding, SeverityLevel
from app.domain.entities.scan_stream import (
    ScanEventType,
    ScanStreamEvent,
    WebSocketConnectionParams,
)
from app.infrastructure.workers.redis_pubsub_manager import (
    MAX_EVENT_PAYLOAD_SIZE,
    RedisPubSubManager,
)
from app.main import app


def test_scan_stream_event_serialization() -> None:
    """Test ScanStreamEvent domain model serialization to dictionary."""
    job_id = uuid4()
    org_id = uuid4()
    event = ScanStreamEvent(
        job_id=job_id,
        organization_id=org_id,
        event_type=ScanEventType.STATE_CHANGE,
        payload={"previous_state": "QUEUED", "new_state": "CRAWLING"},
    )
    d = event.to_dict()
    assert d["job_id"] == str(job_id)
    assert d["organization_id"] == str(org_id)
    assert d["event_type"] == "STATE_CHANGE"
    assert d["payload"]["new_state"] == "CRAWLING"
    assert d["event_id"].startswith("evt_")


@pytest.mark.anyio
async def test_redis_pubsub_manager_channel_and_in_memory_fallback() -> None:
    """Test RedisPubSubManager channel naming and in-memory queue fallback."""
    manager = RedisPubSubManager()
    await manager.clear_in_memory_subscribers()
    org_id = uuid4()
    scan_id = uuid4()

    channel = manager.get_channel_name(org_id, scan_id)
    assert channel == f"vulnova:scan:events:{org_id}:{scan_id}"

    event = ScanStreamEvent(
        job_id=scan_id,
        organization_id=org_id,
        event_type=ScanEventType.PROGRESS_UPDATE,
        payload={"progress_pct": 50},
    )

    # Mock Redis client as None to force in-memory fallback
    with patch.object(manager, "_get_redis_client", return_value=None):
        published = await manager.publish_scan_event(org_id, scan_id, event)
        assert published is True


@pytest.mark.anyio
async def test_redis_pubsub_manager_payload_size_cap() -> None:
    """Test RedisPubSubManager payload size validation enforcing 64KB max cap."""
    manager = RedisPubSubManager()
    org_id = uuid4()
    scan_id = uuid4()

    # Oversized payload exceeding 64KB
    huge_data = "X" * (MAX_EVENT_PAYLOAD_SIZE + 100)
    event = ScanStreamEvent(
        job_id=scan_id,
        organization_id=org_id,
        event_type=ScanEventType.ERROR_LOG,
        payload={"huge_data": huge_data},
    )

    with pytest.raises(ValueError) as exc_info:
        await manager.publish_scan_event(org_id, scan_id, event)
    assert "exceeds MAX_EVENT_PAYLOAD_SIZE limit" in str(exc_info.value)


@pytest.mark.anyio
async def test_scan_event_publisher_service() -> None:
    """Test ScanEventPublisherService helper emission methods."""
    mock_pubsub = AsyncMock(spec=RedisPubSubManager)
    mock_pubsub.publish_scan_event.return_value = True
    publisher = ScanEventPublisherService(pubsub_manager=mock_pubsub)

    org_id = uuid4()
    job_id = uuid4()

    res1 = await publisher.publish_state_change(
        org_id, job_id, "QUEUED", "CRAWLING", "Port Crawl"
    )
    assert res1 is True
    mock_pubsub.publish_scan_event.assert_called_once()

    mock_pubsub.reset_mock()
    res2 = await publisher.publish_plugin_started(
        org_id, job_id, "sql_injection_scanner"
    )
    assert res2 is True
    mock_pubsub.publish_scan_event.assert_called_once()

    mock_pubsub.reset_mock()
    finding = Finding(
        title="SQL Injection",
        severity=SeverityLevel.HIGH,
        category="Injection",
        cve_id="CVE-2024-1234",
    )
    res3 = await publisher.publish_finding_discovered(org_id, job_id, finding)
    assert res3 is True
    mock_pubsub.publish_scan_event.assert_called_once()

    mock_pubsub.reset_mock()
    res4 = await publisher.publish_error(org_id, job_id, "Connection timeout")
    assert res4 is True
    mock_pubsub.publish_scan_event.assert_called_once()


@pytest.mark.anyio
async def test_scan_stream_manager_connection_limits() -> None:
    """Test ScanStreamManagerService max 50 connections per organization limit."""
    manager = ScanStreamManagerService()
    org_id = uuid4()
    scan_id = uuid4()

    # Register 50 dummy sockets
    for i in range(MAX_CONNECTIONS_PER_ORG):
        mock_ws = AsyncMock()
        params = WebSocketConnectionParams(
            user_id=uuid4(), organization_id=org_id, scan_id=scan_id
        )
        await manager.connect(mock_ws, params)

    assert manager.get_organization_connection_count(org_id) == MAX_CONNECTIONS_PER_ORG

    # Attempt 51st connection should raise ForbiddenException
    mock_ws_51 = AsyncMock()
    params_51 = WebSocketConnectionParams(
        user_id=uuid4(), organization_id=org_id, scan_id=scan_id
    )
    with pytest.raises(ForbiddenException) as exc_info:
        await manager.connect(mock_ws_51, params_51)
    assert "Organization connection limit (50) reached" in str(exc_info.value)


@pytest.mark.anyio
async def test_scan_stream_manager_stale_connection_pruning() -> None:
    """Test ScanStreamManagerService pruning connections inactive for >90s."""
    manager = ScanStreamManagerService()
    org_id = uuid4()
    scan_id = uuid4()

    mock_ws = AsyncMock()
    params = WebSocketConnectionParams(
        user_id=uuid4(), organization_id=org_id, scan_id=scan_id
    )
    await manager.connect(mock_ws, params)

    # Set last_active to 100 seconds ago
    past_time = datetime.now(timezone.utc).replace(year=2020)
    manager._last_active[mock_ws] = past_time

    pruned = await manager.prune_stale_connections()
    assert pruned == 1
    assert manager.get_organization_connection_count(org_id) == 0


def test_rest_fallback_event_history_endpoint() -> None:
    """Test GET /api/v1/assessments/{scan_id}/events REST fallback endpoint."""
    client = TestClient(app)
    scan_id = uuid4()
    # Unauthenticated request should return 401
    resp = client.get(f"/api/v1/assessments/{scan_id}/events")
    assert resp.status_code in (401, 403)
