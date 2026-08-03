"""Unit and Integration Tests for Phase 4.7 Enterprise Scan Profile & Execution Policy Engine."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.application.assessment.dto import CreateAssessmentRequest
from app.application.assessment.policy_engine import ScanPolicyEngine
from app.application.assessment.scan_profiles import ScanProfileRegistry
from app.application.assessment.services import AssessmentService
from app.domain.entities.assessment import (
    Finding,
    ScanPolicy,
    ScanProfileType,
    SeverityLevel,
)
from app.infrastructure.assessment.plugins import SecurityHeadersPlugin  # noqa: F401
from app.infrastructure.assessment.registry import PluginRegistry
from app.infrastructure.database.models.user import UserModel


def test_scan_profile_registry_resolution() -> None:
    """Test ScanProfileRegistry resolves valid plugin IDs from PluginRegistry for all 10 profiles."""
    registry = PluginRegistry()
    profile_registry = ScanProfileRegistry(registry)

    profiles = profile_registry.list_profiles()
    assert len(profiles) == 10

    registered_ids = [p.id for p in registry.list_plugins()]

    for p in profiles:
        resolved = profile_registry.resolve_plugins_for_profile(p.id)
        assert isinstance(resolved, list)
        for pid in resolved:
            assert pid in registered_ids


def test_policy_engine_validation() -> None:
    """Test ScanPolicyEngine validates and clamps policy parameters within safe boundaries."""
    policy = ScanPolicy(
        concurrency_limit=100,  # exceeds max 20
        rate_limit_rps=200,  # exceeds max 50
        max_crawl_depth=50,  # exceeds max 10
        max_requests=10000,  # exceeds max 5000
        timeout_seconds=1000.0,  # exceeds max 300.0
    )
    validated = ScanPolicyEngine.validate_policy(policy)
    assert validated.concurrency_limit == 20
    assert validated.rate_limit_rps == 50
    assert validated.max_crawl_depth == 10
    assert validated.max_requests == 5000
    assert validated.timeout_seconds == 300.0


def test_policy_engine_scope_filtering() -> None:
    """Test ScanPolicyEngine URL scope matching with include and exclude patterns."""
    policy = ScanPolicy(
        scope_include_patterns=["https://example.com/api/*"],
        scope_exclude_patterns=["*/logout", "*/admin/*"],
    )

    assert (
        ScanPolicyEngine.is_url_in_scope("https://example.com/api/users", policy)
        is True
    )
    assert (
        ScanPolicyEngine.is_url_in_scope("https://example.com/api/logout", policy)
        is False
    )
    assert (
        ScanPolicyEngine.is_url_in_scope("https://example.com/api/admin/delete", policy)
        is False
    )
    assert (
        ScanPolicyEngine.is_url_in_scope("https://example.com/blog/posts", policy)
        is False
    )


def test_policy_engine_auth_enrichment() -> None:
    """Test header and cookie enrichment in ScanPolicyEngine."""
    policy = ScanPolicy(
        auth_headers={"Authorization": "Bearer test_token"},
        auth_cookies={"session_id": "secret123"},
    )
    headers = ScanPolicyEngine.enrich_request_headers({"Host": "example.com"}, policy)
    assert headers["Host"] == "example.com"
    assert headers["Authorization"] == "Bearer test_token"

    cookies = ScanPolicyEngine.enrich_request_cookies({"theme": "dark"}, policy)
    assert cookies["theme"] == "dark"
    assert cookies["session_id"] == "secret123"


def test_policy_engine_stop_on_critical() -> None:
    """Test critical finding stop condition trigger in ScanPolicyEngine."""
    policy_stop = ScanPolicy(stop_on_critical=True)
    policy_no_stop = ScanPolicy(stop_on_critical=False)

    finding_critical = Finding(
        organization_id=uuid4(),
        title="SQL Injection",
        severity=SeverityLevel.CRITICAL,
    )
    finding_high = Finding(
        organization_id=uuid4(),
        title="XSS",
        severity=SeverityLevel.HIGH,
    )

    assert (
        ScanPolicyEngine.should_stop_on_critical([finding_high], policy_stop) is False
    )
    assert (
        ScanPolicyEngine.should_stop_on_critical([finding_critical], policy_stop)
        is True
    )
    assert (
        ScanPolicyEngine.should_stop_on_critical([finding_critical], policy_no_stop)
        is False
    )


def test_assessment_service_profile_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    """Integration test verifying AssessmentService executes plugins resolved for a specific scan profile."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:

        async def _run() -> None:
            mock_session = AsyncMock()
            service = AssessmentService(mock_session)

            mock_user = MagicMock(spec=UserModel)
            mock_user.id = uuid4()
            mock_user.organization_id = uuid4()

            mock_job = MagicMock()
            mock_job.id = uuid4()
            mock_job.target_url = "https://example.com"
            mock_job.created_at = "2026-08-03T00:00:00Z"
            mock_job.profile_id = ScanProfileType.WEB_SCAN.value
            mock_job.policy_json = {
                "concurrency_limit": 5,
                "rate_limit_rps": 10,
                "respect_robots_txt": True,
                "scope_include_patterns": [],
                "scope_exclude_patterns": [],
                "max_crawl_depth": 3,
                "max_requests": 500,
                "timeout_seconds": 30.0,
                "stop_on_critical": False,
            }

            service.repo.create_job = AsyncMock(return_value=mock_job)
            service.repo.update_job_status = AsyncMock()
            service.repo.create_finding = AsyncMock()

            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.headers = {"content-type": "text/html"}
            mock_resp.text = "<html><body>Test</body></html>"

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
                profile_id=ScanProfileType.WEB_SCAN.value,
                policy_override={"rate_limit_rps": 15},
            )
            res = await service.create_and_run_assessment(req, mock_user)

            assert res.status == "COMPLETED"
            assert res.profile_id == ScanProfileType.WEB_SCAN.value
            assert res.policy is not None
            assert res.policy.rate_limit_rps == 15

        loop.run_until_complete(_run())
    finally:
        loop.close()


def test_list_scan_profiles_endpoint() -> None:
    """Test AssessmentService.list_scan_profiles returns 10 registered scan profile DTOs."""
    mock_session = AsyncMock()
    service = AssessmentService(mock_session)
    profiles = service.list_scan_profiles()
    assert len(profiles) == 10
    profile_ids = [p.id for p in profiles]
    assert ScanProfileType.WEB_SCAN.value in profile_ids
    assert ScanProfileType.API_SCAN.value in profile_ids
    assert ScanProfileType.FULL_ASSESSMENT.value in profile_ids
