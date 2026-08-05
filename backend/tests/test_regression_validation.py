"""Unit and Integration Test Suite for Automated Security Regression Testing Engine."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.routers.regression_validation import (
    get_regression_validation_service,
)
from app.application.regression_validation.dto import (
    RegressionValidationSuiteResponse,
    RegressionValidationSummaryDTO,
)
from app.application.regression_validation.validation_runner import (
    RegressionValidationRunnerService,
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
async def test_regression_suite_execution(mock_analyst_user: UserModel) -> None:
    """Verify executing Security Regression testing suite returns 10 category results."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    service = RegressionValidationRunnerService(mock_session, mock_audit)
    res = await service.run_regression_validation(mock_analyst_user)

    assert res.suite_id is not None
    assert res.total_categories == 10
    assert len(res.category_results) == 10
    assert res.overall_pass_rate == 100.0
    mock_audit.record_event.assert_called()


@pytest.mark.anyio
async def test_regression1_owasp_web_validation(mock_analyst_user: UserModel) -> None:
    """Verify REGRESSION1 OWASP Web Top 10 checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = RegressionValidationRunnerService(mock_session, mock_audit)

    res = service.check_regression1_owasp_web([])
    assert res.category_code == "REGRESSION1"
    assert res.status == "PASSED"
    assert "FastAPI" in (res.affected_component or "")


@pytest.mark.anyio
async def test_regression2_owasp_api_validation(mock_analyst_user: UserModel) -> None:
    """Verify REGRESSION2 OWASP API Security checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = RegressionValidationRunnerService(mock_session, mock_audit)

    res = service.check_regression2_owasp_api([])
    assert res.category_code == "REGRESSION2"
    assert res.status == "PASSED"
    assert "REST API" in (res.affected_component or "")


@pytest.mark.anyio
async def test_regression3_infrastructure_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify REGRESSION3 Security Config & Infrastructure checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = RegressionValidationRunnerService(mock_session, mock_audit)

    res = service.check_regression3_infrastructure([])
    assert res.category_code == "REGRESSION3"
    assert res.status == "PASSED"
    assert "Middleware" in (res.affected_component or "")


@pytest.mark.anyio
async def test_regression5_sca_supply_chain_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify REGRESSION5 SCA Supply Chain checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = RegressionValidationRunnerService(mock_session, mock_audit)

    res = service.check_regression5_sca_supply_chain([])
    assert res.category_code == "REGRESSION5"
    assert res.status == "PASSED"
    assert "Lockfiles" in (res.affected_component or "")


@pytest.mark.anyio
async def test_regression6_container_hardening_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify REGRESSION6 Container Security checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = RegressionValidationRunnerService(mock_session, mock_audit)

    res = service.check_regression6_container_hardening([])
    assert res.category_code == "REGRESSION6"
    assert res.status == "PASSED"
    assert "Dockerfile" in (res.affected_component or "")


@pytest.mark.anyio
async def test_regression7_secrets_crypto_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify REGRESSION7 Secrets & Cryptographic checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = RegressionValidationRunnerService(mock_session, mock_audit)

    res = service.check_regression7_secrets_crypto([])
    assert res.category_code == "REGRESSION7"
    assert res.status == "PASSED"
    assert "CryptoService" in (res.affected_component or "")


@pytest.mark.anyio
async def test_regression8_stride_threat_model_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify REGRESSION8 STRIDE Threat Model checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = RegressionValidationRunnerService(mock_session, mock_audit)

    res = service.check_regression8_stride_threat_model([])
    assert res.category_code == "REGRESSION8"
    assert res.status == "PASSED"
    assert "STRIDE" in (res.affected_component or "")


@pytest.mark.anyio
async def test_regression_rbac_permissions(
    mock_analyst_user: UserModel,
    mock_viewer_user: UserModel,
) -> None:
    """Verify RBAC permissions for security regression testing endpoints."""
    mock_service = AsyncMock()
    mock_suite_response = RegressionValidationSuiteResponse(
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
    mock_summary_response = RegressionValidationSummaryDTO(
        organization_id=str(mock_analyst_user.organization_id),
        last_executed_at="2026-08-05T20:00:00Z",
        overall_pass_rate=100.0,
        overall_status="PASSED",
        passed_categories=10,
        failed_categories=0,
    )

    mock_service.run_regression_validation.return_value = mock_suite_response
    mock_service.get_latest_summary.return_value = mock_summary_response

    app.dependency_overrides[get_regression_validation_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = lambda: mock_viewer_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Viewer can read regression summary/results
        res_summary = await client.get("/api/v1/validation/regression/summary")
        assert res_summary.status_code == 200

        # Viewer CANNOT execute suite (requires validation:execute / SECURITY_ANALYST+)
        res_run = await client.post("/api/v1/validation/regression/run")
        assert res_run.status_code == 403

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_regression_audit_logging(mock_analyst_user: UserModel) -> None:
    """Verify audit log records for validation.regression_suite_started and validation.regression_suite_completed."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    service = RegressionValidationRunnerService(mock_session, mock_audit)
    await service.run_regression_validation(mock_analyst_user)

    assert mock_audit.record_event.call_count >= 2
