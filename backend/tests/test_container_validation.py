"""Unit and Integration Test Suite for Container Image Security & Runtime Hardening Engine."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.routers.container_validation import get_container_validation_service
from app.application.container_validation.dto import (
    ContainerValidationSuiteResponse,
    ContainerValidationSummaryDTO,
)
from app.application.container_validation.validation_runner import (
    ContainerValidationRunnerService,
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
async def test_container_suite_execution(mock_analyst_user: UserModel) -> None:
    """Verify executing Container validation suite returns 10 category results."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    service = ContainerValidationRunnerService(mock_session, mock_audit)
    res = await service.run_container_validation(mock_analyst_user)

    assert res.suite_id is not None
    assert res.total_categories == 10
    assert len(res.category_results) == 10
    assert res.overall_pass_rate > 0.0
    mock_audit.record_event.assert_called()


@pytest.mark.anyio
async def test_container1_base_image_cves_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify CONTAINER1 base image CVE checks and controlled status handling."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = ContainerValidationRunnerService(mock_session, mock_audit)

    res = service.check_container1_base_image_cves([])
    assert res.category_code == "CONTAINER1"
    assert res.status in ("PASSED", "WARNING")
    assert "Base Images" in (res.affected_container or "")


@pytest.mark.anyio
async def test_container2_non_root_user_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify CONTAINER2 unprivileged user execution checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = ContainerValidationRunnerService(mock_session, mock_audit)

    res = service.check_container2_non_root_user([])
    assert res.category_code == "CONTAINER2"
    assert res.status == "PASSED"
    assert "User" in (res.affected_container or "")


@pytest.mark.anyio
async def test_container4_capability_drop_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify CONTAINER4 capability drop checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = ContainerValidationRunnerService(mock_session, mock_audit)

    res = service.check_container4_capability_drop([])
    assert res.category_code == "CONTAINER4"
    assert res.status == "PASSED"
    assert "Capabilities" in (res.affected_container or "")


@pytest.mark.anyio
async def test_container5_healthcheck_validation(mock_analyst_user: UserModel) -> None:
    """Verify CONTAINER5 healthcheck directive checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = ContainerValidationRunnerService(mock_session, mock_audit)

    res = service.check_container5_healthcheck([])
    assert res.category_code == "CONTAINER5"
    assert res.status == "PASSED"
    assert "HEALTHCHECK" in (res.affected_container or "")


@pytest.mark.anyio
async def test_container7_resource_limits_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify CONTAINER7 cgroup resource limit checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = ContainerValidationRunnerService(mock_session, mock_audit)

    res = service.check_container7_resource_limits([])
    assert res.category_code == "CONTAINER7"
    assert res.status == "PASSED"
    assert "Resource" in (res.affected_container or "")


@pytest.mark.anyio
async def test_container8_network_isolation_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify CONTAINER8 network isolation checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = ContainerValidationRunnerService(mock_session, mock_audit)

    res = service.check_container8_network_isolation([])
    assert res.category_code == "CONTAINER8"
    assert res.status == "PASSED"
    assert "Networks" in (res.affected_container or "")


@pytest.mark.anyio
async def test_container10_digest_pinning_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify CONTAINER10 image digest pinning checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = ContainerValidationRunnerService(mock_session, mock_audit)

    res = service.check_container10_digest_pinning([])
    assert res.category_code == "CONTAINER10"
    assert res.status == "PASSED"
    assert "Directives" in (res.affected_container or "")


@pytest.mark.anyio
async def test_container_rbac_permissions(
    mock_analyst_user: UserModel,
    mock_viewer_user: UserModel,
) -> None:
    """Verify RBAC permissions for container security validation endpoints."""
    mock_service = AsyncMock()
    mock_suite_response = ContainerValidationSuiteResponse(
        suite_id=str(uuid4()),
        organization_id=str(mock_analyst_user.organization_id),
        executed_at="2026-08-05T18:00:00Z",
        overall_status="PASSED",
        overall_pass_rate=100.0,
        passed_categories=10,
        failed_categories=0,
        warning_categories=0,
        total_categories=10,
        category_results=[],
    )
    mock_summary_response = ContainerValidationSummaryDTO(
        organization_id=str(mock_analyst_user.organization_id),
        last_executed_at="2026-08-05T18:00:00Z",
        overall_pass_rate=100.0,
        overall_status="PASSED",
        passed_categories=10,
        failed_categories=0,
    )

    mock_service.run_container_validation.return_value = mock_suite_response
    mock_service.get_latest_summary.return_value = mock_summary_response

    app.dependency_overrides[get_container_validation_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = lambda: mock_viewer_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Viewer can read container validation summary/results
        res_summary = await client.get("/api/v1/validation/container/summary")
        assert res_summary.status_code == 200

        # Viewer CANNOT execute suite (requires validation:execute / SECURITY_ANALYST+)
        res_run = await client.post("/api/v1/validation/container/run")
        assert res_run.status_code == 403

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_container_audit_logging(mock_analyst_user: UserModel) -> None:
    """Verify audit log records for validation.container_suite_started and validation.container_suite_completed."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    service = ContainerValidationRunnerService(mock_session, mock_audit)
    await service.run_container_validation(mock_analyst_user)

    assert mock_audit.record_event.call_count >= 2
