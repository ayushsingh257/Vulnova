"""Unit and Integration Tests for Vulnerability Assessment Engine & Plugin Framework."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.assessment.dto import CreateAssessmentRequest
from app.application.assessment.services import AssessmentService
from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.domain.entities.assessment import (
    AssessmentContext,
    AssessmentJobStatus,
    PluginStatus,
    SeverityLevel,
    VulnerabilityCategory,
)
from app.domain.entities.discovery import AssetNodeType
from app.infrastructure.assessment.plugins.headers_plugin import (
    SecurityHeadersPlugin,
)
from app.infrastructure.assessment.registry import PluginRegistry
from app.infrastructure.database.models.user import UserModel


def test_assessment_domain_enums() -> None:
    """Test vulnerability assessment domain enum values."""
    assert SeverityLevel.CRITICAL.value == "CRITICAL"
    assert SeverityLevel.HIGH.value == "HIGH"
    assert VulnerabilityCategory.SECURITY_HEADER.value == "SECURITY_HEADER"
    assert PluginStatus.REGISTERED.value == "REGISTERED"
    assert AssessmentJobStatus.COMPLETED.value == "COMPLETED"


def test_plugin_registry_lifecycle() -> None:
    """Test PluginRegistry registration, retrieval, and listing."""
    registry = PluginRegistry()
    registry.clear()

    plugin = SecurityHeadersPlugin()
    registry.register(plugin)

    assert "security_headers_plugin" in registry.list_plugin_ids()
    retrieved = registry.get_plugin("security_headers_plugin")
    assert retrieved is not None
    assert retrieved.metadata.name == "HTTP Security Headers Auditor"
    assert AssetNodeType.TARGET_DOMAIN in retrieved.metadata.supported_asset_types


def test_security_headers_plugin_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test SecurityHeadersPlugin executes against target URL and returns standardized Finding objects."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            plugin = SecurityHeadersPlugin()
            ctx = AssessmentContext(
                target_url="https://example.com",
                target_domain="example.com",
                organization_id=uuid4(),
            )

            # Mock httpx response with missing headers
            mock_resp = MagicMock()
            mock_resp.headers = {"content-type": "text/html"}

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: mock_client)

            findings = await plugin.execute(ctx)
            assert len(findings) >= 3
            severities = [f.severity for f in findings]
            assert SeverityLevel.HIGH in severities
            assert SeverityLevel.MEDIUM in severities

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_assessment_service_ssrf_rejection() -> None:
    """Test AssessmentService rejects private IP target URLs for vulnerability scanning."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = AssessmentService(mock_session)

            mock_user = MagicMock(spec=UserModel)
            mock_user.id = uuid4()
            mock_user.organization_id = uuid4()

            req = CreateAssessmentRequest(
                target_url="http://127.0.0.1/scan",
                is_authorized_assessment=True,
            )
            service.assessment_policy_engine.validate_scan_authorization = AsyncMock(
                return_value=MagicMock(is_allowed=True, rejection_reason=None)
            )
            with pytest.raises(ValidationException) as exc_info:
                await service.create_and_run_assessment(req, mock_user)

            assert "prohibited" in str(exc_info.value).lower()

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_assessment_service_run_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test AssessmentService creates job, executes registered plugins, and records audit trail."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = AssessmentService(mock_session)

            mock_user = MagicMock(spec=UserModel)
            mock_user.id = uuid4()
            mock_user.organization_id = uuid4()

            service.assessment_policy_engine.validate_scan_authorization = AsyncMock(
                return_value=MagicMock(is_allowed=True, rejection_reason=None)
            )

            # Mock Repository job
            mock_job = MagicMock()
            mock_job.id = uuid4()
            mock_job.target_url = "https://example.com"
            mock_job.execution_state = "QUEUED"
            mock_job.created_at = "2026-08-02T16:00:00Z"
            service.repo.create_job = AsyncMock(return_value=mock_job)
            service.repo.get_job_by_id = AsyncMock(return_value=mock_job)
            service.repo.update_execution_state = AsyncMock(return_value=mock_job)
            service.repo.update_job_status = AsyncMock()
            service.repo.create_finding = AsyncMock()

            # Mock plugin execution returning 0 findings for speed
            mock_plugin = AsyncMock()
            mock_plugin.execute.return_value = []

            service.plugin_registry.clear()
            mock_meta = MagicMock()
            mock_meta.id = "mock_plugin"
            mock_plugin.metadata = mock_meta
            service.plugin_registry.register(mock_plugin)

            req = CreateAssessmentRequest(
                target_url="https://example.com",
                is_authorized_assessment=True,
            )
            res = await service.create_and_run_assessment(req, mock_user)

            assert res.target_url == "https://example.com"
            assert res.status == "COMPLETED"
            service.repo.create_job.assert_called_once()
            service.repo.update_execution_state.assert_called()

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_assessment_service_get_job_not_found() -> None:
    """Test get_assessment_job raises ResourceNotFoundException when job is missing or belongs to another tenant."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = AssessmentService(mock_session)

            mock_user = MagicMock(spec=UserModel)
            mock_user.id = uuid4()
            mock_user.organization_id = uuid4()

            service.repo.get_job_by_id = AsyncMock(return_value=None)

            random_id = uuid4()
            with pytest.raises(ResourceNotFoundException) as exc_info:
                await service.get_assessment_job(random_id, mock_user)

            assert "not found" in str(exc_info.value).lower()

        loop.run_until_complete(_run())
    finally:
        loop.close()
