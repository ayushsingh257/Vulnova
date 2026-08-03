"""Unit and Integration Tests for Phase 4.3 API Security Assessment Plugins."""

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
from app.infrastructure.assessment.plugins.api_security_plugin import (
    APISecurityPlugin,
)
from app.infrastructure.assessment.plugins.auth_plugin import AuthSecurityPlugin
from app.infrastructure.assessment.plugins.cors_plugin import CORSPlugin
from app.infrastructure.assessment.plugins.headers_plugin import (
    SecurityHeadersPlugin,
)
from app.infrastructure.assessment.plugins.jwt_security_plugin import (
    JWTSecurityPlugin,
)
from app.infrastructure.assessment.plugins.sql_injection_plugin import (
    SQLInjectionPlugin,
)
from app.infrastructure.assessment.plugins.xss_plugin import XSSPlugin
from app.infrastructure.assessment.registry import PluginRegistry
from app.infrastructure.database.models.user import UserModel


def test_api_plugins_registration() -> None:
    """Test APISecurityPlugin, JWTSecurityPlugin, and CORSPlugin auto-registration."""
    registry = PluginRegistry()
    registry.register(SecurityHeadersPlugin())
    registry.register(SQLInjectionPlugin())
    registry.register(XSSPlugin())
    registry.register(AuthSecurityPlugin())
    registry.register(APISecurityPlugin())
    registry.register(JWTSecurityPlugin())
    registry.register(CORSPlugin())

    plugin_ids = registry.list_plugin_ids()

    assert "api_security_plugin" in plugin_ids
    assert "jwt_security_plugin" in plugin_ids
    assert "cors_security_plugin" in plugin_ids

    api_p = registry.get_plugin("api_security_plugin")
    assert api_p is not None
    assert api_p.metadata.category == VulnerabilityCategory.INFORMATION_DISCLOSURE

    jwt_p = registry.get_plugin("jwt_security_plugin")
    assert jwt_p is not None
    assert jwt_p.metadata.category == VulnerabilityCategory.AUTHENTICATION

    cors_p = registry.get_plugin("cors_security_plugin")
    assert cors_p is not None
    assert cors_p.metadata.category == VulnerabilityCategory.MISCONFIGURATION


def test_api_security_plugin_doc_exposure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test APISecurityPlugin detects exposed API documentation endpoints."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            plugin = APISecurityPlugin()
            ctx = AssessmentContext(
                target_url="https://example.com/api/v1",
                target_domain="example.com",
                organization_id=uuid4(),
            )

            # Mock httpx response returning Swagger UI html for /swagger-ui
            def mock_get(url: str, **kwargs) -> MagicMock:
                mock_resp = MagicMock()
                if "swagger-ui" in url:
                    mock_resp.status_code = 200
                    mock_resp.headers = {"content-type": "text/html"}
                    mock_resp.text = (
                        "<html><head><title>Swagger UI</title></head></html>"
                    )
                else:
                    mock_resp.status_code = 404
                    mock_resp.headers = {}
                    mock_resp.text = "Not Found"
                return mock_resp

            mock_client = AsyncMock()
            mock_client.get.side_effect = mock_get
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: mock_client)

            findings = await plugin.execute(ctx)
            assert len(findings) >= 1
            f = findings[0]
            assert f.severity == SeverityLevel.MEDIUM
            assert f.category == VulnerabilityCategory.INFORMATION_DISCLOSURE
            assert f.cwe_id == "CWE-200"

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_jwt_security_plugin_unsigned_token() -> None:
    """Test JWTSecurityPlugin detects unsigned JWT ('alg': 'none')."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            plugin = JWTSecurityPlugin()

            # Header: {"alg":"none","typ":"JWT"} -> eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0
            # Payload: {"sub":"1234567890","name":"John Doe","iat":1516239022} -> eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ
            unsigned_jwt = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ."

            ctx = AssessmentContext(
                target_url="https://example.com/api",
                target_domain="example.com",
                organization_id=uuid4(),
                options={"jwt_token": unsigned_jwt},
            )

            findings = await plugin.execute(ctx)
            assert len(findings) >= 2  # alg=none and missing exp
            alg_none_f = next(f for f in findings if "Unsigned Token" in f.title)
            assert alg_none_f.severity == SeverityLevel.CRITICAL
            assert alg_none_f.cwe_id == "CWE-347"

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_cors_plugin_wildcard_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test CORSPlugin detects wildcard origin with credentials allowed."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            plugin = CORSPlugin()
            ctx = AssessmentContext(
                target_url="https://example.com/api/data",
                target_domain="example.com",
                organization_id=uuid4(),
            )

            mock_headers = MagicMock()
            mock_headers.get.side_effect = lambda k: {
                "access-control-allow-origin": "*",
                "access-control-allow-credentials": "true",
            }.get(k.lower())

            mock_resp = MagicMock()
            mock_resp.headers = mock_headers

            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None

            monkeypatch.setattr("httpx.AsyncClient", lambda **kwargs: mock_client)

            findings = await plugin.execute(ctx)
            assert len(findings) >= 1
            f = findings[0]
            assert f.severity == SeverityLevel.HIGH
            assert f.category == VulnerabilityCategory.MISCONFIGURATION
            assert f.cwe_id == "CWE-942"

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_assessment_service_executes_all_seven_plugins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test AssessmentService executes all 7 registered security plugins through generic pipeline."""
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

            mock_user = MagicMock(spec=UserModel)
            mock_user.id = uuid4()
            mock_user.organization_id = uuid4()

            mock_job = MagicMock()
            mock_job.id = uuid4()
            mock_job.target_url = "https://example.com"
            mock_job.execution_state = "QUEUED"
            mock_job.created_at = "2026-08-02T17:00:00Z"
            service.repo.create_job = AsyncMock(return_value=mock_job)
            service.repo.get_job_by_id = AsyncMock(return_value=mock_job)
            service.repo.update_execution_state = AsyncMock(return_value=mock_job)
            service.repo.update_job_status = AsyncMock()
            service.repo.create_finding = AsyncMock()

            # Mock httpx for all plugins
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

            service.assessment_policy_engine.validate_scan_authorization = AsyncMock(
                return_value=MagicMock(is_allowed=True, rejection_reason=None)
            )

            req = CreateAssessmentRequest(
                target_url="https://example.com",
                is_authorized_assessment=True,
            )
            res = await service.create_and_run_assessment(req, mock_user)

            assert res.status == "COMPLETED"
            assert len(res.enabled_plugins) == 7
            assert "api_security_plugin" in res.enabled_plugins
            assert "jwt_security_plugin" in res.enabled_plugins
            assert "cors_security_plugin" in res.enabled_plugins

        loop.run_until_complete(_run())
    finally:
        loop.close()
