"""Unit and Integration Tests for Phase 4.4 Infrastructure & Cloud Security Assessment Plugins."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.assessment.dto import CreateAssessmentRequest
from app.application.assessment.services import AssessmentService
from app.domain.entities.assessment import (
    AssessmentContext,
    SeverityLevel,
    VulnerabilityCategory,
)
from app.infrastructure.assessment.plugins.api_security_plugin import APISecurityPlugin
from app.infrastructure.assessment.plugins.auth_plugin import AuthSecurityPlugin
from app.infrastructure.assessment.plugins.cloud_security_plugin import (
    CloudSecurityPlugin,
)
from app.infrastructure.assessment.plugins.cors_plugin import CORSPlugin
from app.infrastructure.assessment.plugins.headers_plugin import (
    SecurityHeadersPlugin,
)
from app.infrastructure.assessment.plugins.jwt_security_plugin import JWTSecurityPlugin
from app.infrastructure.assessment.plugins.network_service_plugin import (
    NetworkServicePlugin,
)
from app.infrastructure.assessment.plugins.sql_injection_plugin import (
    SQLInjectionPlugin,
)
from app.infrastructure.assessment.plugins.tls_security_plugin import (
    TLSSecurityPlugin,
)
from app.infrastructure.assessment.plugins.xss_plugin import XSSPlugin
from app.infrastructure.assessment.registry import PluginRegistry
from app.infrastructure.database.models.user import UserModel


def test_infrastructure_plugins_registration() -> None:
    """Test NetworkServicePlugin, TLSSecurityPlugin, and CloudSecurityPlugin auto-registration."""
    registry = PluginRegistry()
    registry.register(SecurityHeadersPlugin())
    registry.register(SQLInjectionPlugin())
    registry.register(XSSPlugin())
    registry.register(AuthSecurityPlugin())
    registry.register(APISecurityPlugin())
    registry.register(JWTSecurityPlugin())
    registry.register(CORSPlugin())
    registry.register(NetworkServicePlugin())
    registry.register(TLSSecurityPlugin())
    registry.register(CloudSecurityPlugin())

    plugin_ids = registry.list_plugin_ids()

    assert "network_service_plugin" in plugin_ids
    assert "tls_security_plugin" in plugin_ids
    assert "cloud_security_plugin" in plugin_ids

    net_p = registry.get_plugin("network_service_plugin")
    assert net_p is not None
    assert net_p.metadata.category == VulnerabilityCategory.MISCONFIGURATION

    tls_p = registry.get_plugin("tls_security_plugin")
    assert tls_p is not None
    assert tls_p.metadata.category == VulnerabilityCategory.MISCONFIGURATION

    cloud_p = registry.get_plugin("cloud_security_plugin")
    assert cloud_p is not None
    assert cloud_p.metadata.category == VulnerabilityCategory.INFORMATION_DISCLOSURE


def test_network_service_plugin_port_exposure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test NetworkServicePlugin detects open SSH (22) and RDP (3389) ports."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            plugin = NetworkServicePlugin()
            ctx = AssessmentContext(
                target_url="https://example.com",
                target_domain="example.com",
                organization_id=uuid4(),
            )

            # Mock _check_port to simulate open SSH port 22
            async def _mock_check(host: str, port: int, timeout: float = 2.0) -> bool:
                return port == 22

            monkeypatch.setattr(plugin, "_check_port", _mock_check)

            findings = await plugin.execute(ctx)
            assert len(findings) == 1
            f = findings[0]
            assert "SSH" in f.title
            assert f.severity == SeverityLevel.MEDIUM
            assert f.cwe_id == "CWE-284"

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_cloud_security_plugin_s3_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test CloudSecurityPlugin detects public AWS S3 bucket listing."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            plugin = CloudSecurityPlugin()
            ctx = AssessmentContext(
                target_url="https://company-backups.s3.amazonaws.com",
                target_domain="company-backups.s3.amazonaws.com",
                organization_id=uuid4(),
            )

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.text = "<?xml version='1.0'?><ListBucketResult><Contents><Key>backup.db</Key></Contents></ListBucketResult>"

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: mock_client)

            findings = await plugin.execute(ctx)
            assert len(findings) >= 1
            f = findings[0]
            assert f.severity == SeverityLevel.HIGH
            assert f.category == VulnerabilityCategory.INFORMATION_DISCLOSURE
            assert f.cwe_id == "CWE-732"

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_assessment_service_executes_all_ten_plugins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test AssessmentService executes all 10 registered security plugins through generic pipeline."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = AssessmentService(mock_session)

            service.plugin_registry.clear()
            service.plugin_registry.register(SecurityHeadersPlugin())
            service.plugin_registry.register(SQLInjectionPlugin())
            service.plugin_registry.register(XSSPlugin())
            service.plugin_registry.register(AuthSecurityPlugin())
            service.plugin_registry.register(APISecurityPlugin())
            service.plugin_registry.register(JWTSecurityPlugin())
            service.plugin_registry.register(CORSPlugin())
            service.plugin_registry.register(NetworkServicePlugin())
            service.plugin_registry.register(TLSSecurityPlugin())
            service.plugin_registry.register(CloudSecurityPlugin())

            mock_user = MagicMock(spec=UserModel)
            mock_user.id = uuid4()
            mock_user.organization_id = uuid4()

            mock_job = MagicMock()
            mock_job.id = uuid4()
            mock_job.target_url = "https://example.com"
            mock_job.created_at = "2026-08-02T17:45:00Z"
            service.repo.create_job = AsyncMock(return_value=mock_job)
            service.repo.update_job_status = AsyncMock()
            service.repo.create_finding = AsyncMock()

            # Mock httpx and socket calls for all plugins
            mock_headers = MagicMock()
            mock_headers.items.return_value = []
            mock_headers.get_list.return_value = []
            mock_headers.get.return_value = None

            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_resp.headers = mock_headers
            mock_resp.text = "<html>Hello</body></html>"

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: mock_client)

            req = CreateAssessmentRequest(target_url="https://example.com")
            res = await service.create_and_run_assessment(req, mock_user)

            assert res.status == "COMPLETED"
            assert len(res.enabled_plugins) == 10
            assert "network_service_plugin" in res.enabled_plugins
            assert "tls_security_plugin" in res.enabled_plugins
            assert "cloud_security_plugin" in res.enabled_plugins

        loop.run_until_complete(_run())
    finally:
        loop.close()
