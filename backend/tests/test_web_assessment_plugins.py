"""Unit and Integration Tests for Phase 4.2 Web Vulnerability Assessment Plugins."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import unquote
from uuid import uuid4

import pytest

from app.application.assessment.dto import CreateAssessmentRequest
from app.application.assessment.services import AssessmentService
from app.domain.entities.assessment import (
    AssessmentContext,
    SeverityLevel,
    VulnerabilityCategory,
)
from app.domain.entities.discovery import AssetNodeType
from app.infrastructure.assessment.plugins.auth_plugin import AuthSecurityPlugin
from app.infrastructure.assessment.plugins.headers_plugin import SecurityHeadersPlugin
from app.infrastructure.assessment.plugins.sql_injection_plugin import (
    SQLInjectionPlugin,
)
from app.infrastructure.assessment.plugins.xss_plugin import XSSPlugin
from app.infrastructure.assessment.registry import PluginRegistry
from app.infrastructure.database.models.user import UserModel


def test_web_plugins_registration() -> None:
    """Test SQLInjectionPlugin, XSSPlugin, and AuthSecurityPlugin auto-registration."""
    registry = PluginRegistry()
    registry.register(SecurityHeadersPlugin())
    registry.register(SQLInjectionPlugin())
    registry.register(XSSPlugin())
    registry.register(AuthSecurityPlugin())

    plugin_ids = registry.list_plugin_ids()

    assert "sql_injection_plugin" in plugin_ids
    assert "xss_plugin" in plugin_ids
    assert "auth_security_plugin" in plugin_ids
    assert "security_headers_plugin" in plugin_ids

    sqli = registry.get_plugin("sql_injection_plugin")
    assert sqli is not None
    assert sqli.metadata.category == VulnerabilityCategory.INJECTION

    xss = registry.get_plugin("xss_plugin")
    assert xss is not None
    assert xss.metadata.category == VulnerabilityCategory.INJECTION

    auth = registry.get_plugin("auth_security_plugin")
    assert auth is not None
    assert auth.metadata.category == VulnerabilityCategory.AUTHENTICATION


def test_sql_injection_plugin_detection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test SQLInjectionPlugin detects SQL error signatures and generates Findings."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            plugin = SQLInjectionPlugin()
            ctx = AssessmentContext(
                target_url="https://example.com/search?q=test",
                target_domain="example.com",
                organization_id=uuid4(),
            )

            # Mock httpx response with SQL syntax error
            mock_resp = MagicMock()
            mock_resp.text = 'ERROR: syntax error at or near "\'" at character 14'

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: mock_client)

            findings = await plugin.execute(ctx)
            assert len(findings) >= 1
            sqli_finding = findings[0]
            assert sqli_finding.severity == SeverityLevel.CRITICAL
            assert sqli_finding.category == VulnerabilityCategory.INJECTION
            assert sqli_finding.cwe_id == "CWE-89"
            assert "probe_url" in sqli_finding.evidence

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_xss_plugin_detection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test XSSPlugin detects unescaped HTML payload reflection."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            plugin = XSSPlugin()
            ctx = AssessmentContext(
                target_url="https://example.com/search?q=test",
                target_domain="example.com",
                organization_id=uuid4(),
            )

            # Mock httpx response returning unquoted reflected payload
            def mock_get(url: str, **kwargs) -> MagicMock:
                mock_resp = MagicMock()
                mock_resp.text = f"<html>Search results for {unquote(url)}</html>"
                return mock_resp

            mock_client = AsyncMock()
            mock_client.get.side_effect = mock_get
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: mock_client)

            findings = await plugin.execute(ctx)
            assert len(findings) >= 1
            xss_finding = findings[0]
            assert xss_finding.severity == SeverityLevel.HIGH
            assert xss_finding.category == VulnerabilityCategory.INJECTION
            assert xss_finding.cwe_id == "CWE-79"

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_auth_security_plugin_cookie_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test AuthSecurityPlugin detects insecure cookie flags."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            plugin = AuthSecurityPlugin()
            ctx = AssessmentContext(
                target_url="https://example.com/login",
                target_domain="example.com",
                organization_id=uuid4(),
            )

            # Mock headers with insecure Set-Cookie
            mock_headers = MagicMock()
            mock_headers.get_list.return_value = ["session_id=abc12345; Path=/"]

            mock_resp = MagicMock()
            mock_resp.headers = mock_headers

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: mock_client)

            findings = await plugin.execute(ctx)
            assert len(findings) >= 2
            titles = [f.title for f in findings]
            assert any("Missing HttpOnly Flag" in t for t in titles)
            assert any("Missing Secure Flag" in t for t in titles)

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_assessment_service_executes_registered_plugins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test AssessmentService executes all 4 registered web vulnerability plugins through generic pipeline."""
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

            mock_user = MagicMock(spec=UserModel)
            mock_user.id = uuid4()
            mock_user.organization_id = uuid4()

            mock_job = MagicMock()
            mock_job.id = uuid4()
            mock_job.target_url = "https://example.com"
            mock_job.execution_state = "QUEUED"
            mock_job.created_at = "2026-08-02T16:30:00Z"
            service.repo.create_job = AsyncMock(return_value=mock_job)
            service.repo.get_job_by_id = AsyncMock(return_value=mock_job)
            service.repo.update_execution_state = AsyncMock(return_value=mock_job)
            service.repo.update_job_status = AsyncMock()
            service.repo.create_finding = AsyncMock()

            # Mock httpx for all plugins
            mock_headers = MagicMock()
            mock_headers.items.return_value = []
            mock_headers.get_list.return_value = []

            mock_resp = MagicMock()
            mock_resp.headers = mock_headers
            mock_resp.text = "<html>Hello</body></html>"

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: mock_client)

            service.assessment_policy_engine.validate_scan_authorization = AsyncMock(
                return_value=MagicMock(is_allowed=True, rejection_reason=None)
            )

            req = CreateAssessmentRequest(
                target_url="https://example.com",
                is_authorized_assessment=True,
            )
            res = await service.create_and_run_assessment(req, mock_user)

            assert res.status == "COMPLETED"
            assert len(res.enabled_plugins) == 4
            assert "sql_injection_plugin" in res.enabled_plugins
            assert "xss_plugin" in res.enabled_plugins
            assert "auth_security_plugin" in res.enabled_plugins
            assert "security_headers_plugin" in res.enabled_plugins

        loop.run_until_complete(_run())
    finally:
        loop.close()
