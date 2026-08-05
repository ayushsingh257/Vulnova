"""Unit and Integration Test Suite for Secrets & Cryptographic Management Engine."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.routers.secrets_validation import get_secrets_validation_service
from app.application.secrets_validation.dto import (
    SecretsValidationSuiteResponse,
    SecretsValidationSummaryDTO,
)
from app.application.secrets_validation.validation_runner import (
    SecretsValidationRunnerService,
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
async def test_secrets_suite_execution(mock_analyst_user: UserModel) -> None:
    """Verify executing Secrets validation suite returns 10 category results."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    service = SecretsValidationRunnerService(mock_session, mock_audit)
    res = await service.run_secrets_validation(mock_analyst_user)

    assert res.suite_id is not None
    assert res.total_categories == 10
    assert len(res.category_results) == 10
    assert res.overall_pass_rate > 0.0
    mock_audit.record_event.assert_called()


@pytest.mark.anyio
async def test_secret1_gitleaks_hardcoded_secrets_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify SECRET1 Gitleaks hardcoded secret checks and controlled status handling."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = SecretsValidationRunnerService(mock_session, mock_audit)

    res = service.check_secret1_gitleaks_hardcoded_secrets([])
    assert res.category_code == "SECRET1"
    assert res.status in ("PASSED", "WARNING")
    assert "Gitleaks" in (res.affected_secret or "")


@pytest.mark.anyio
async def test_secret2_envelope_encryption_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify SECRET2 AES-256-GCM envelope encryption checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = SecretsValidationRunnerService(mock_session, mock_audit)

    res = service.check_secret2_envelope_encryption([])
    assert res.category_code == "SECRET2"
    assert res.status == "PASSED"
    assert "AES-256-GCM" in (res.affected_secret or "")


@pytest.mark.anyio
async def test_secret3_jwt_secret_strength_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify SECRET3 JWT signing key entropy checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = SecretsValidationRunnerService(mock_session, mock_audit)

    res = service.check_secret3_jwt_secret_strength([])
    assert res.category_code == "SECRET3"
    assert res.status in ("PASSED", "WARNING")
    assert "JWT" in (res.affected_secret or "")


@pytest.mark.anyio
async def test_secret4_api_key_hashing_validation(mock_analyst_user: UserModel) -> None:
    """Verify SECRET4 API key cryptographic storage checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = SecretsValidationRunnerService(mock_session, mock_audit)

    res = service.check_secret4_api_key_hashing([])
    assert res.category_code == "SECRET4"
    assert res.status == "PASSED"
    assert "SHA-256" in (res.affected_secret or "")


@pytest.mark.anyio
async def test_secret5_webhook_hmac_signatures_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify SECRET5 webhook HMAC signature checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = SecretsValidationRunnerService(mock_session, mock_audit)

    res = service.check_secret5_webhook_hmac_signatures([])
    assert res.category_code == "SECRET5"
    assert res.status == "PASSED"
    assert "HMAC" in (res.affected_secret or "")


@pytest.mark.anyio
async def test_secret6_tls_encryption_in_transit_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify SECRET6 TLS & encryption in transit checks."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = SecretsValidationRunnerService(mock_session, mock_audit)

    res = service.check_secret6_tls_encryption_in_transit([])
    assert res.category_code == "SECRET6"
    assert res.status == "PASSED"
    assert "TLS" in (res.affected_secret or "")


@pytest.mark.anyio
async def test_secret7_key_rotation_policy_validation(
    mock_analyst_user: UserModel,
) -> None:
    """Verify SECRET7 key rotation policy checks without inventing fake history."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = SecretsValidationRunnerService(mock_session, mock_audit)

    res = service.check_secret7_key_rotation_policy([])
    assert res.category_code == "SECRET7"
    assert res.status in ("PASSED", "WARNING")
    assert "Rotation" in (res.affected_secret or "")


@pytest.mark.anyio
async def test_secrets_rbac_permissions(
    mock_analyst_user: UserModel,
    mock_viewer_user: UserModel,
) -> None:
    """Verify RBAC permissions for secrets security validation endpoints."""
    mock_service = AsyncMock()
    mock_suite_response = SecretsValidationSuiteResponse(
        suite_id=str(uuid4()),
        organization_id=str(mock_analyst_user.organization_id),
        executed_at="2026-08-05T19:00:00Z",
        overall_status="PASSED",
        overall_pass_rate=100.0,
        passed_categories=10,
        failed_categories=0,
        warning_categories=0,
        total_categories=10,
        category_results=[],
    )
    mock_summary_response = SecretsValidationSummaryDTO(
        organization_id=str(mock_analyst_user.organization_id),
        last_executed_at="2026-08-05T19:00:00Z",
        overall_pass_rate=100.0,
        overall_status="PASSED",
        passed_categories=10,
        failed_categories=0,
    )

    mock_service.run_secrets_validation.return_value = mock_suite_response
    mock_service.get_latest_summary.return_value = mock_summary_response

    app.dependency_overrides[get_secrets_validation_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = lambda: mock_viewer_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Viewer can read secrets validation summary/results
        res_summary = await client.get("/api/v1/validation/secrets/summary")
        assert res_summary.status_code == 200

        # Viewer CANNOT execute suite (requires validation:execute / SECURITY_ANALYST+)
        res_run = await client.post("/api/v1/validation/secrets/run")
        assert res_run.status_code == 403

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_secrets_audit_logging(mock_analyst_user: UserModel) -> None:
    """Verify audit log records for validation.secrets_suite_started and validation.secrets_suite_completed."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result.scalars.return_value = mock_scalars
    mock_session.execute.return_value = mock_result

    service = SecretsValidationRunnerService(mock_session, mock_audit)
    await service.run_secrets_validation(mock_analyst_user)

    assert mock_audit.record_event.call_count >= 2
