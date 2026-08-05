"""Unit and Integration Test Suite for OWASP API Security Top 10 (2023) Validation Engine."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.routers.api_security_validation import get_api_validation_service
from app.application.api_security_validation.dto import (
    APIValidationSuiteResponse,
    APIValidationSummaryDTO,
)
from app.application.api_security_validation.validation_runner import (
    APISecurityValidationRunnerService,
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
async def test_api_security_suite_execution(mock_analyst_user: UserModel) -> None:
    """Verify executing API security validation suite returns 10 category results."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    service = APISecurityValidationRunnerService(mock_session, mock_audit)
    res = await service.run_api_security_validation(mock_analyst_user)

    assert res.suite_id is not None
    assert res.total_categories == 10
    assert len(res.category_results) == 10
    assert res.overall_pass_rate == 100.0
    assert res.overall_status == "PASSED"
    mock_audit.record_event.assert_called()


@pytest.mark.anyio
async def test_api1_bola_validation(mock_analyst_user: UserModel) -> None:
    """Verify API1:2023 BOLA evaluation and subsystem guidance."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = APISecurityValidationRunnerService(mock_session, mock_audit)

    mock_finding = MagicMock()
    mock_finding.id = uuid4()
    mock_finding.title = "BOLA Vulnerability in Asset Fetch Router"
    mock_finding.category = "bola"
    mock_finding.severity = "CRITICAL"
    mock_finding.status = "OPEN"

    res = service.check_api1_bola([mock_finding])
    assert res.category_code == "API1:2023"
    assert res.finding_count == 1
    assert res.status in ("WARNING", "FAILED")
    assert res.affected_subsystem == "OrganizationIsolation & DatabaseRepository"


@pytest.mark.anyio
async def test_api2_authentication_validation(mock_analyst_user: UserModel) -> None:
    """Verify API2:2023 Broken Authentication evaluation."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = APISecurityValidationRunnerService(mock_session, mock_audit)

    res = service.check_api2_authentication([])
    assert res.category_code == "API2:2023"
    assert res.status == "PASSED"
    assert res.pass_rate_percentage == 100.0


@pytest.mark.anyio
async def test_api3_property_authorization_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify API3:2023 Broken Object Property Level Authorization evaluation."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = APISecurityValidationRunnerService(mock_session, mock_audit)

    res = service.check_api3_property_authorization([])
    assert res.category_code == "API3:2023"
    assert res.status == "PASSED"
    assert res.affected_subsystem == "PydanticDTO & SecretEncryptionService"


@pytest.mark.anyio
async def test_api4_rate_limit_validation(mock_analyst_user: UserModel) -> None:
    """Verify API4:2023 Unrestricted Resource Consumption evaluation."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = APISecurityValidationRunnerService(mock_session, mock_audit)

    res = service.check_api4_resource_consumption([])
    assert res.category_code == "API4:2023"
    assert res.status == "PASSED"
    assert res.affected_subsystem == "RateLimiter & FastAPIBodyLimit"


@pytest.mark.anyio
async def test_api5_function_authorization_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify API5:2023 Broken Function Level Authorization evaluation."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = APISecurityValidationRunnerService(mock_session, mock_audit)

    res = service.check_api5_function_authorization([])
    assert res.category_code == "API5:2023"
    assert res.status == "PASSED"
    assert res.affected_subsystem == "RBACPolicy & RolePermissionMap"


@pytest.mark.anyio
async def test_api7_ssrf_validation(mock_analyst_user: UserModel) -> None:
    """Verify API7:2023 SSRF validator checks and private IP blocking."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = APISecurityValidationRunnerService(mock_session, mock_audit)

    res = service.check_api7_ssrf([])
    assert res.category_code == "API7:2023"
    assert res.status == "PASSED"
    assert res.affected_subsystem == "SSRFValidator & TargetUrlFilter"


@pytest.mark.anyio
async def test_api_tenant_isolation(mock_analyst_user: UserModel) -> None:
    """Verify tenant isolation on API security validation queries."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    service = APISecurityValidationRunnerService(mock_session, mock_audit)
    res = await service.run_api_security_validation(mock_analyst_user)
    assert res.organization_id == str(mock_analyst_user.organization_id)


@pytest.mark.anyio
async def test_api_rbac_permissions(
    mock_analyst_user: UserModel,
    mock_viewer_user: UserModel,
) -> None:
    """Verify RBAC permissions for API security validation endpoints."""
    mock_service = AsyncMock()
    mock_suite_response = APIValidationSuiteResponse(
        suite_id=str(uuid4()),
        organization_id=str(mock_analyst_user.organization_id),
        executed_at="2026-08-05T16:00:00Z",
        overall_status="PASSED",
        overall_pass_rate=100.0,
        passed_categories=10,
        failed_categories=0,
        warning_categories=0,
        total_categories=10,
        category_results=[],
    )
    mock_summary_response = APIValidationSummaryDTO(
        organization_id=str(mock_analyst_user.organization_id),
        last_executed_at="2026-08-05T16:00:00Z",
        overall_pass_rate=100.0,
        overall_status="PASSED",
        passed_categories=10,
        failed_categories=0,
    )

    mock_service.run_api_security_validation.return_value = mock_suite_response
    mock_service.get_latest_summary.return_value = mock_summary_response

    app.dependency_overrides[get_api_validation_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = lambda: mock_viewer_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Viewer can read validation summary/results
        res_summary = await client.get("/api/v1/validation/api-security/summary")
        assert res_summary.status_code == 200

        # Viewer CANNOT execute validation suite (requires validation:execute / SECURITY_ANALYST+)
        res_run = await client.post("/api/v1/validation/api-security/run")
        assert res_run.status_code == 403

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_api_security_audit_logging(mock_analyst_user: UserModel) -> None:
    """Verify audit log records for validation.api_security_suite_started and validation.api_security_suite_completed."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    service = APISecurityValidationRunnerService(mock_session, mock_audit)
    await service.run_api_security_validation(mock_analyst_user)

    assert mock_audit.record_event.call_count >= 2
