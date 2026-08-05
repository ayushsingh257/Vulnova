"""Unit and Integration Test Suite for Security Control Plane Final Certification & Compliance Engine."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.routers.certification_validation import (
    get_certification_validation_service,
)
from app.application.certification_validation.dto import (
    CertificationValidationSuiteResponse,
    CertificationValidationSummaryDTO,
)
from app.application.certification_validation.validation_runner import (
    CertificationValidationRunnerService,
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
async def test_certification_suite_execution(mock_analyst_user: UserModel) -> None:
    """Verify executing Security Certification testing suite returns 10 category results."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    service = CertificationValidationRunnerService(mock_session, mock_audit)
    res = await service.run_certification_validation(mock_analyst_user)

    assert res.suite_id is not None
    assert res.total_categories == 10
    assert len(res.category_results) == 10
    assert res.overall_certification_score == 100.0
    mock_audit.record_event.assert_called()


@pytest.mark.anyio
async def test_certification_owasp_controls(mock_analyst_user: UserModel) -> None:
    """Verify CERTIFICATION1 OWASP controls."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = CertificationValidationRunnerService(mock_session, mock_audit)

    res = service.check_certification1_owasp_controls([])
    assert res.category_code == "CERTIFICATION1"
    assert res.status == "PASSED"
    assert "OWASP" in (res.affected_control or "")


@pytest.mark.anyio
async def test_certification_infrastructure_controls(
    mock_analyst_user: UserModel,
) -> None:
    """Verify CERTIFICATION2 Infrastructure controls."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = CertificationValidationRunnerService(mock_session, mock_audit)

    res = service.check_certification2_infrastructure_controls([])
    assert res.category_code == "CERTIFICATION2"
    assert res.status == "PASSED"
    assert "Headers" in (res.affected_control or "") or "Middleware" in (
        res.affected_control or ""
    )


@pytest.mark.anyio
async def test_certification_pentest_controls(mock_analyst_user: UserModel) -> None:
    """Verify CERTIFICATION3 Pentest readiness controls."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = CertificationValidationRunnerService(mock_session, mock_audit)

    res = service.check_certification3_pentest_readiness([])
    assert res.category_code == "CERTIFICATION3"
    assert res.status == "PASSED"
    assert "Exploit" in (res.affected_control or "")


@pytest.mark.anyio
async def test_certification_supply_chain_controls(
    mock_analyst_user: UserModel,
) -> None:
    """Verify CERTIFICATION4 Supply chain controls."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = CertificationValidationRunnerService(mock_session, mock_audit)

    res = service.check_certification4_supply_chain_controls([])
    assert res.category_code == "CERTIFICATION4"
    assert res.status == "PASSED"
    assert "SCA" in (res.affected_control or "") or "Lockfile" in (
        res.affected_control or ""
    )


@pytest.mark.anyio
async def test_certification_container_controls(mock_analyst_user: UserModel) -> None:
    """Verify CERTIFICATION5 Container security controls."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = CertificationValidationRunnerService(mock_session, mock_audit)

    res = service.check_certification5_container_controls([])
    assert res.category_code == "CERTIFICATION5"
    assert res.status == "PASSED"
    assert "Container" in (res.affected_control or "")


@pytest.mark.anyio
async def test_certification_crypto_controls(mock_analyst_user: UserModel) -> None:
    """Verify CERTIFICATION6 Secrets and cryptographic controls."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = CertificationValidationRunnerService(mock_session, mock_audit)

    res = service.check_certification6_crypto_controls([])
    assert res.category_code == "CERTIFICATION6"
    assert res.status == "PASSED"
    assert "CryptoService" in (res.affected_control or "")


@pytest.mark.anyio
async def test_certification_stride_controls(mock_analyst_user: UserModel) -> None:
    """Verify CERTIFICATION7 Threat model and STRIDE controls."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = CertificationValidationRunnerService(mock_session, mock_audit)

    res = service.check_certification7_stride_controls([])
    assert res.category_code == "CERTIFICATION7"
    assert res.status == "PASSED"
    assert "STRIDE" in (res.affected_control or "")


@pytest.mark.anyio
async def test_certification_rbac_permissions(
    mock_analyst_user: UserModel,
    mock_viewer_user: UserModel,
) -> None:
    """Verify RBAC permissions for security certification testing endpoints."""
    mock_service = AsyncMock()
    mock_suite_response = CertificationValidationSuiteResponse(
        suite_id=str(uuid4()),
        organization_id=str(mock_analyst_user.organization_id),
        executed_at="2026-08-05T21:00:00Z",
        overall_status="PASSED",
        overall_certification_score=100.0,
        passed_categories=10,
        failed_categories=0,
        warning_categories=0,
        total_categories=10,
        category_results=[],
    )
    mock_summary_response = CertificationValidationSummaryDTO(
        organization_id=str(mock_analyst_user.organization_id),
        last_executed_at="2026-08-05T21:00:00Z",
        overall_certification_score=100.0,
        overall_status="PASSED",
        passed_categories=10,
        failed_categories=0,
    )

    mock_service.run_certification_validation.return_value = mock_suite_response
    mock_service.get_latest_summary.return_value = mock_summary_response

    app.dependency_overrides[get_certification_validation_service] = (
        lambda: mock_service
    )
    app.dependency_overrides[get_current_user] = lambda: mock_viewer_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Viewer can read certification summary/results
        res_summary = await client.get("/api/v1/validation/certification/summary")
        assert res_summary.status_code == 200

        # Viewer CANNOT execute suite (requires validation:execute / SECURITY_ANALYST+)
        res_run = await client.post("/api/v1/validation/certification/run")
        assert res_run.status_code == 403

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_certification_audit_logging(mock_analyst_user: UserModel) -> None:
    """Verify audit log records for validation.certification_suite_started and validation.certification_suite_completed."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    service = CertificationValidationRunnerService(mock_session, mock_audit)
    await service.run_certification_validation(mock_analyst_user)

    assert mock_audit.record_event.call_count >= 2
