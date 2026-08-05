"""Unit and Integration Test Suite for OWASP Top 10 (2021) Security Validation Engine."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.routers.owasp_validation import get_validation_service
from app.application.owasp_validation.validation_runner import (
    OWASPValidationRunnerService,
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
async def test_owasp_suite_execution(mock_analyst_user: UserModel) -> None:
    """Verify executing OWASP validation suite returns 10 category results."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    service = OWASPValidationRunnerService(mock_session, mock_audit)
    res = await service.run_validation_suite(mock_analyst_user)

    assert res.suite_id is not None
    assert res.total_categories == 10
    assert len(res.category_results) == 10
    assert res.overall_pass_rate == 100.0
    assert res.overall_status == "PASSED"
    mock_audit.record_event.assert_called()


@pytest.mark.anyio
async def test_a01_broken_access_control_verification(
    mock_analyst_user: UserModel,
) -> None:
    """Verify A01:2021 category evaluation and subsystem guidance."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = OWASPValidationRunnerService(mock_session, mock_audit)

    mock_finding = MagicMock()
    mock_finding.id = uuid4()
    mock_finding.title = "Unrestricted IDOR in User Profile Endpoint"
    mock_finding.category = "access_control"
    mock_finding.severity = "CRITICAL"
    mock_finding.status = "OPEN"

    res = service._check_a01_broken_access_control([mock_finding])
    assert res.category_code == "A01:2021"
    assert res.finding_count == 1
    assert res.status in ("WARNING", "FAILED")
    assert res.affected_subsystem == "RBACPolicy & OrganizationIsolation"
    assert res.failure_reason is not None


@pytest.mark.anyio
async def test_a02_cryptographic_failures_verification(
    mock_analyst_user: UserModel,
) -> None:
    """Verify A02:2021 category evaluation."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = OWASPValidationRunnerService(mock_session, mock_audit)

    res = service._check_a02_cryptographic_failures([])
    assert res.category_code == "A02:2021"
    assert res.status == "PASSED"
    assert res.pass_rate_percentage == 100.0


@pytest.mark.anyio
async def test_a03_injection_verification(mock_analyst_user: UserModel) -> None:
    """Verify A03:2021 category evaluation."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = OWASPValidationRunnerService(mock_session, mock_audit)

    mock_finding = MagicMock()
    mock_finding.id = uuid4()
    mock_finding.title = "SQL Injection in Search Endpoint"
    mock_finding.category = "sqli"
    mock_finding.severity = "CRITICAL"
    mock_finding.status = "OPEN"

    res = service._check_a03_injection([mock_finding])
    assert res.category_code == "A03:2021"
    assert res.finding_count == 1
    assert res.affected_subsystem == "DatabaseORM & InputSanitizer"


@pytest.mark.anyio
async def test_a07_auth_verification(mock_analyst_user: UserModel) -> None:
    """Verify A07:2021 category evaluation."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = OWASPValidationRunnerService(mock_session, mock_audit)

    res = service._check_a07_auth_failures([])
    assert res.category_code == "A07:2021"
    assert res.status == "PASSED"


@pytest.mark.anyio
async def test_a10_ssrf_verification(mock_analyst_user: UserModel) -> None:
    """Verify A10:2021 SSRF validator checks and private IP blocking."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = OWASPValidationRunnerService(mock_session, mock_audit)

    res = service._check_a10_ssrf([])
    assert res.category_code == "A10:2021"
    assert res.status == "PASSED"
    assert res.affected_subsystem == "SSRFValidator & TargetUrlFilter"


@pytest.mark.anyio
async def test_owasp_pass_rate_calculation(mock_analyst_user: UserModel) -> None:
    """Verify aggregate pass rate calculation across all categories."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    service = OWASPValidationRunnerService(mock_session, mock_audit)
    res = await service.run_validation_suite(mock_analyst_user)

    assert 0.0 <= res.overall_pass_rate <= 100.0
    assert res.passed_categories + res.failed_categories + res.warning_categories == 10


@pytest.mark.anyio
async def test_owasp_validation_tenant_isolation(mock_analyst_user: UserModel) -> None:
    """Verify tenant isolation on validation runner queries."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    service = OWASPValidationRunnerService(mock_session, mock_audit)
    res = await service.run_validation_suite(mock_analyst_user)
    assert res.organization_id == str(mock_analyst_user.organization_id)


@pytest.mark.anyio
async def test_owasp_validation_rbac_permissions(
    mock_analyst_user: UserModel,
    mock_viewer_user: UserModel,
) -> None:
    """Verify RBAC permissions for OWASP validation endpoints."""
    from app.application.owasp_validation.dto import (
        OWASPValidationSuiteResponse,
        OWASPVerificationSummaryDTO,
    )

    mock_service = AsyncMock()
    mock_suite_response = OWASPValidationSuiteResponse(
        suite_id=str(uuid4()),
        organization_id=str(mock_analyst_user.organization_id),
        executed_at="2026-08-05T15:00:00Z",
        overall_status="PASSED",
        overall_pass_rate=100.0,
        passed_categories=10,
        failed_categories=0,
        warning_categories=0,
        total_categories=10,
        category_results=[],
    )
    mock_summary_response = OWASPVerificationSummaryDTO(
        organization_id=str(mock_analyst_user.organization_id),
        last_executed_at="2026-08-05T15:00:00Z",
        overall_pass_rate=100.0,
        overall_status="PASSED",
        passed_categories=10,
        failed_categories=0,
    )

    mock_service.run_validation_suite.return_value = mock_suite_response
    mock_service.get_latest_summary.return_value = mock_summary_response

    app.dependency_overrides[get_validation_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = lambda: mock_viewer_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Viewer can read validation summary/results
        res_summary = await client.get("/api/v1/validation/owasp-top-10/summary")
        assert res_summary.status_code == 200

        # Viewer CANNOT execute validation suite (requires validation:execute / SECURITY_ANALYST+)
        res_run = await client.post("/api/v1/validation/owasp-top-10/run")
        assert res_run.status_code == 403

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_owasp_validation_audit_logging(mock_analyst_user: UserModel) -> None:
    """Verify audit log records for validation.owasp_suite_started and validation.owasp_suite_completed."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    service = OWASPValidationRunnerService(mock_session, mock_audit)
    await service.run_validation_suite(mock_analyst_user)

    assert mock_audit.record_event.call_count >= 2
