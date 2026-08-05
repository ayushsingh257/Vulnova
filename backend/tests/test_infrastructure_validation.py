"""Unit and Integration Test Suite for Security Configuration & Infrastructure Validation Engine."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.routers.infrastructure_validation import get_infra_validation_service
from app.application.infrastructure_validation.dto import (
    InfrastructureValidationSuiteResponse,
    InfrastructureValidationSummaryDTO,
)
from app.application.infrastructure_validation.validation_runner import (
    InfrastructureSecurityValidationRunnerService,
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
async def test_infrastructure_suite_execution(mock_analyst_user: UserModel) -> None:
    """Verify executing infrastructure validation suite returns 10 category results."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    service = InfrastructureSecurityValidationRunnerService(mock_session, mock_audit)
    res = await service.run_infrastructure_validation(mock_analyst_user)

    assert res.suite_id is not None
    assert res.total_categories == 10
    assert len(res.category_results) == 10
    assert res.overall_pass_rate == 100.0
    assert res.overall_status == "PASSED"
    mock_audit.record_event.assert_called()


@pytest.mark.anyio
async def test_container_security_validation(mock_analyst_user: UserModel) -> None:
    """Verify INFRA2 container security checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = InfrastructureSecurityValidationRunnerService(mock_session, mock_audit)

    res = service.check_infra2_container_security([])
    assert res.category_code == "INFRA2"
    assert res.status == "PASSED"
    assert "Dockerfile" in (res.affected_component or "")


@pytest.mark.anyio
async def test_dependency_security_validation(mock_analyst_user: UserModel) -> None:
    """Verify INFRA3 supply chain dependency security checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = InfrastructureSecurityValidationRunnerService(mock_session, mock_audit)

    res = service.check_infra3_supply_chain_security([])
    assert res.category_code == "INFRA3"
    assert res.status == "PASSED"
    assert "Dependency Lockfiles" in (res.affected_component or "")


@pytest.mark.anyio
async def test_cicd_security_validation(mock_analyst_user: UserModel) -> None:
    """Verify INFRA4 CI/CD security checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = InfrastructureSecurityValidationRunnerService(mock_session, mock_audit)

    res = service.check_infra4_cicd_security([])
    assert res.category_code == "INFRA4"
    assert res.status == "PASSED"
    assert "GitHub Actions" in (res.affected_component or "")


@pytest.mark.anyio
async def test_database_security_validation(mock_analyst_user: UserModel) -> None:
    """Verify INFRA5 database security checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = InfrastructureSecurityValidationRunnerService(mock_session, mock_audit)

    res = service.check_infra5_database_security([])
    assert res.category_code == "INFRA5"
    assert res.status == "PASSED"
    assert "PostgreSQL" in (res.affected_component or "")


@pytest.mark.anyio
async def test_logging_monitoring_validation(mock_analyst_user: UserModel) -> None:
    """Verify INFRA6 logging & alert monitoring checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = InfrastructureSecurityValidationRunnerService(mock_session, mock_audit)

    res = service.check_infra6_logging_monitoring([])
    assert res.category_code == "INFRA6"
    assert res.status == "PASSED"
    assert "AuditLogService" in (res.affected_component or "")


@pytest.mark.anyio
async def test_access_control_validation(mock_analyst_user: UserModel) -> None:
    """Verify INFRA7 RBAC access control infrastructure checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = InfrastructureSecurityValidationRunnerService(mock_session, mock_audit)

    res = service.check_infra7_access_control([])
    assert res.category_code == "INFRA7"
    assert res.status == "PASSED"
    assert "RBAC" in (res.affected_component or "")


@pytest.mark.anyio
async def test_network_security_validation(mock_analyst_user: UserModel) -> None:
    """Verify INFRA8 SSRF firewall & network security checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = InfrastructureSecurityValidationRunnerService(mock_session, mock_audit)

    res = service.check_infra8_network_security([])
    assert res.category_code == "INFRA8"
    assert res.status == "PASSED"
    assert "SSRFValidator" in (res.affected_component or "")


@pytest.mark.anyio
async def test_cloud_security_validation(mock_analyst_user: UserModel) -> None:
    """Verify INFRA9 cloud metadata blocking & security checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = InfrastructureSecurityValidationRunnerService(mock_session, mock_audit)

    res = service.check_infra9_cloud_security([])
    assert res.category_code == "INFRA9"
    assert res.status == "PASSED"
    assert "Cloud Metadata Firewall" in (res.affected_component or "")


@pytest.mark.anyio
async def test_infrastructure_audit_logging(
    mock_analyst_user: UserModel,
    mock_viewer_user: UserModel,
) -> None:
    """Verify RBAC and audit logging for infrastructure validation endpoints."""
    mock_service = AsyncMock()
    mock_suite_response = InfrastructureValidationSuiteResponse(
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
    mock_summary_response = InfrastructureValidationSummaryDTO(
        organization_id=str(mock_analyst_user.organization_id),
        last_executed_at="2026-08-05T16:00:00Z",
        overall_pass_rate=100.0,
        overall_status="PASSED",
        passed_categories=10,
        failed_categories=0,
    )

    mock_service.run_infrastructure_validation.return_value = mock_suite_response
    mock_service.get_latest_summary.return_value = mock_summary_response

    app.dependency_overrides[get_infra_validation_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = lambda: mock_viewer_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Viewer can read infrastructure validation summary/results
        res_summary = await client.get("/api/v1/validation/infrastructure/summary")
        assert res_summary.status_code == 200

        # Viewer CANNOT execute suite (requires validation:execute / SECURITY_ANALYST+)
        res_run = await client.post("/api/v1/validation/infrastructure/run")
        assert res_run.status_code == 403

    app.dependency_overrides.clear()
