"""Unit and Integration Test Suite for Threat Model Review & STRIDE Verification Engine."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.routers.threat_validation import get_threat_validation_service
from app.application.threat_validation.dto import (
    ThreatValidationSuiteResponse,
    ThreatValidationSummaryDTO,
)
from app.application.threat_validation.validation_runner import (
    ThreatValidationRunnerService,
)
from app.infrastructure.database.models.user import UserModel
from app.main import app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def mock_analyst_user() -> UserModel:
    user = MagicMock(spec=UserModel)
    user.id = uuid4()
    user.organization_id = uuid4()
    user.email = "analyst@enterprise.com"
    user.full_name = "Security Analyst"
    user.role = "SECURITY_ANALYST"
    user.is_active = True
    return user


@pytest.fixture
def mock_viewer_user(mock_analyst_user: UserModel) -> UserModel:
    user = MagicMock(spec=UserModel)
    user.id = uuid4()
    user.organization_id = mock_analyst_user.organization_id
    user.email = "viewer@enterprise.com"
    user.full_name = "Security Viewer"
    user.role = "VIEWER"
    user.is_active = True
    return user


@pytest.mark.anyio
async def test_threat_suite_execution(mock_analyst_user: UserModel) -> None:
    """Verify executing Threat Model validation suite returns 10 category results."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    service = ThreatValidationRunnerService(mock_session, mock_audit)
    res = await service.run_threat_validation(mock_analyst_user)

    assert res.suite_id is not None
    assert res.total_categories == 10
    assert len(res.category_results) == 10
    assert res.overall_pass_rate == 100.0
    mock_audit.record_event.assert_called()


@pytest.mark.anyio
async def test_stride1_spoofing_identity_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify STRIDE1 identity authentication checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = ThreatValidationRunnerService(mock_session, mock_audit)

    res = service.check_stride1_spoofing_identity([])
    assert res.category_code == "STRIDE1"
    assert res.status == "PASSED"
    assert "JWT" in (res.affected_component or "")


@pytest.mark.anyio
async def test_stride2_spoofing_api_keys_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify STRIDE2 API key authentication checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = ThreatValidationRunnerService(mock_session, mock_audit)

    res = service.check_stride2_spoofing_api_keys([])
    assert res.category_code == "STRIDE2"
    assert res.status == "PASSED"
    assert "API Key" in (res.affected_component or "")


@pytest.mark.anyio
async def test_stride3_tampering_input_injection_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify STRIDE3 input injection tampering checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = ThreatValidationRunnerService(mock_session, mock_audit)

    res = service.check_stride3_tampering_input_injection([])
    assert res.category_code == "STRIDE3"
    assert res.status == "PASSED"
    assert "FastAPI" in (res.affected_component or "")


@pytest.mark.anyio
async def test_stride4_tampering_webhook_signatures_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify STRIDE4 webhook HMAC signature checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = ThreatValidationRunnerService(mock_session, mock_audit)

    res = service.check_stride4_tampering_webhook_signatures([])
    assert res.category_code == "STRIDE4"
    assert res.status == "PASSED"
    assert "HMAC" in (res.affected_component or "")


@pytest.mark.anyio
async def test_stride5_repudiation_audit_logging_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify STRIDE5 non-repudiation audit logging checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = ThreatValidationRunnerService(mock_session, mock_audit)

    res = service.check_stride5_repudiation_audit_logging([])
    assert res.category_code == "STRIDE5"
    assert res.status == "PASSED"
    assert "AuditLogService" in (res.affected_component or "")


@pytest.mark.anyio
async def test_stride6_information_disclosure_multitenancy_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify STRIDE6 multi-tenant boundary isolation checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = ThreatValidationRunnerService(mock_session, mock_audit)

    res = service.check_stride6_information_disclosure_multitenancy([])
    assert res.category_code == "STRIDE6"
    assert res.status == "PASSED"
    assert "organization_id" in (res.affected_component or "")


@pytest.mark.anyio
async def test_stride7_information_disclosure_crypto_egress_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify STRIDE7 sensitive field encryption & egress safeguards."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = ThreatValidationRunnerService(mock_session, mock_audit)

    res = service.check_stride7_information_disclosure_crypto_egress([])
    assert res.category_code == "STRIDE7"
    assert res.status == "PASSED"
    assert "AES-256-GCM" in (res.affected_component or "")


@pytest.mark.anyio
async def test_threat_rbac_permissions(
    mock_analyst_user: UserModel,
    mock_viewer_user: UserModel,
) -> None:
    """Verify RBAC permissions for threat model validation endpoints."""
    mock_service = AsyncMock()
    mock_suite_response = ThreatValidationSuiteResponse(
        suite_id=str(uuid4()),
        organization_id=str(mock_analyst_user.organization_id),
        executed_at="2026-08-05T20:00:00Z",
        overall_status="PASSED",
        overall_pass_rate=100.0,
        passed_categories=10,
        failed_categories=0,
        warning_categories=0,
        total_categories=10,
        category_results=[],
    )
    mock_summary_response = ThreatValidationSummaryDTO(
        organization_id=str(mock_analyst_user.organization_id),
        last_executed_at="2026-08-05T20:00:00Z",
        overall_pass_rate=100.0,
        overall_status="PASSED",
        passed_categories=10,
        failed_categories=0,
    )

    mock_service.run_threat_validation.return_value = mock_suite_response
    mock_service.get_latest_summary.return_value = mock_summary_response

    app.dependency_overrides[get_threat_validation_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = lambda: mock_viewer_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Viewer can read threat validation summary/results
        res_summary = await client.get("/api/v1/validation/threat/summary")
        assert res_summary.status_code == 200

        # Viewer CANNOT execute suite (requires validation:execute / SECURITY_ANALYST+)
        res_run = await client.post("/api/v1/validation/threat/run")
        assert res_run.status_code == 403

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_threat_audit_logging(mock_analyst_user: UserModel) -> None:
    """Verify audit log records for validation.threat_suite_started and validation.threat_suite_completed."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    service = ThreatValidationRunnerService(mock_session, mock_audit)
    await service.run_threat_validation(mock_analyst_user)

    assert mock_audit.record_event.call_count >= 2
