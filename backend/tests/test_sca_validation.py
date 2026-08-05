"""Unit and Integration Test Suite for Dependency Security Audit & SCA Enforcement Engine."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.routers.sca_validation import get_sca_validation_service
from app.application.sca_validation.dto import (
    SCAValidationSuiteResponse,
    SCAValidationSummaryDTO,
)
from app.application.sca_validation.validation_runner import (
    SCAValidationRunnerService,
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
async def test_sca_suite_execution(mock_analyst_user: UserModel) -> None:
    """Verify executing SCA validation suite returns 10 category results."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    service = SCAValidationRunnerService(mock_session, mock_audit)
    res = await service.run_sca_validation(mock_analyst_user)

    assert res.suite_id is not None
    assert res.total_categories == 10
    assert len(res.category_results) == 10
    assert res.overall_pass_rate == 100.0
    assert res.overall_status == "PASSED"
    mock_audit.record_event.assert_called()


@pytest.mark.anyio
async def test_sca1_cve_vulnerabilities_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify SCA1 CVE vulnerability checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = SCAValidationRunnerService(mock_session, mock_audit)

    res = service.check_sca1_cve_vulnerabilities([])
    assert res.category_code == "SCA1"
    assert res.status == "PASSED"
    assert "PyPI" in (res.affected_package or "")


@pytest.mark.anyio
async def test_sca2_lockfile_integrity_validation(mock_analyst_user: UserModel) -> None:
    """Verify SCA2 lockfile integrity checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = SCAValidationRunnerService(mock_session, mock_audit)

    res = service.check_sca2_lockfile_integrity([])
    assert res.category_code == "SCA2"
    assert res.status == "PASSED"
    assert "Lockfiles" in (res.affected_package or "")


@pytest.mark.anyio
async def test_sca3_outdated_dependencies_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify SCA3 outdated dependency checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = SCAValidationRunnerService(mock_session, mock_audit)

    res = service.check_sca3_outdated_dependencies([])
    assert res.category_code == "SCA3"
    assert res.status == "PASSED"
    assert "Libraries" in (res.affected_package or "")


@pytest.mark.anyio
async def test_sca4_pipeline_enforcement_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify SCA4 CI/CD pipeline gate enforcement checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = SCAValidationRunnerService(mock_session, mock_audit)

    res = service.check_sca4_pipeline_enforcement([])
    assert res.category_code == "SCA4"
    assert res.status == "PASSED"
    assert "GitHub Actions" in (res.affected_package or "")


@pytest.mark.anyio
async def test_sca5_license_compliance_validation(mock_analyst_user: UserModel) -> None:
    """Verify SCA5 open-source license compliance checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = SCAValidationRunnerService(mock_session, mock_audit)

    res = service.check_sca5_license_compliance([])
    assert res.category_code == "SCA5"
    assert res.status == "PASSED"
    assert "Licenses" in (res.affected_package or "")


@pytest.mark.anyio
async def test_sca8_version_pinning_validation(mock_analyst_user: UserModel) -> None:
    """Verify SCA8 dependency pinning checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = SCAValidationRunnerService(mock_session, mock_audit)

    res = service.check_sca8_version_pinning([])
    assert res.category_code == "SCA8"
    assert res.status == "PASSED"
    assert "Manifests" in (res.affected_package or "")


@pytest.mark.anyio
async def test_sca9_db_engine_dependencies_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify SCA9 DB and engine driver security checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = SCAValidationRunnerService(mock_session, mock_audit)

    res = service.check_sca9_db_engine_dependencies([])
    assert res.category_code == "SCA9"
    assert res.status == "PASSED"
    assert "Drivers" in (res.affected_package or "")


@pytest.mark.anyio
async def test_sca_rbac_permissions(
    mock_analyst_user: UserModel,
    mock_viewer_user: UserModel,
) -> None:
    """Verify RBAC permissions for dependency security validation endpoints."""
    mock_service = AsyncMock()
    mock_suite_response = SCAValidationSuiteResponse(
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
    mock_summary_response = SCAValidationSummaryDTO(
        organization_id=str(mock_analyst_user.organization_id),
        last_executed_at="2026-08-05T16:00:00Z",
        overall_pass_rate=100.0,
        overall_status="PASSED",
        passed_categories=10,
        failed_categories=0,
    )

    mock_service.run_sca_validation.return_value = mock_suite_response
    mock_service.get_latest_summary.return_value = mock_summary_response

    app.dependency_overrides[get_sca_validation_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = lambda: mock_viewer_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Viewer can read SCA validation summary/results
        res_summary = await client.get("/api/v1/validation/sca/summary")
        assert res_summary.status_code == 200

        # Viewer CANNOT execute suite (requires validation:execute / SECURITY_ANALYST+)
        res_run = await client.post("/api/v1/validation/sca/run")
        assert res_run.status_code == 403

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_sca_audit_logging(mock_analyst_user: UserModel) -> None:
    """Verify audit log records for validation.sca_suite_started and validation.sca_suite_completed."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    service = SCAValidationRunnerService(mock_session, mock_audit)
    await service.run_sca_validation(mock_analyst_user)

    assert mock_audit.record_event.call_count >= 2
