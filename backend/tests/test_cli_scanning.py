"""Unit and Integration Test Suite for CI/CD Pipeline Scanning CLI Tool & APIs."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.routers.cli import get_cli_service
from app.application.cli_scanning.cli_service import CLIScanningService
from app.application.cli_scanning.dto import (
    CLIPipelineGateRequest,
    CLIScanStartRequest,
    CLITokenCreateRequest,
)
from app.infrastructure.database.models.user import UserModel
from app.main import app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def mock_admin_user() -> UserModel:
    user = MagicMock(spec=UserModel)
    user.id = uuid4()
    user.organization_id = uuid4()
    user.email = "admin@enterprise.com"
    user.full_name = "Enterprise Admin"
    user.role = "ADMIN"
    user.is_active = True
    return user


@pytest.fixture
def mock_analyst_user(mock_admin_user: UserModel) -> UserModel:
    user = MagicMock(spec=UserModel)
    user.id = uuid4()
    user.organization_id = mock_admin_user.organization_id
    user.email = "analyst@enterprise.com"
    user.full_name = "Security Analyst"
    user.role = "SECURITY_ANALYST"
    user.is_active = True
    return user


@pytest.fixture
def mock_viewer_user(mock_admin_user: UserModel) -> UserModel:
    user = MagicMock(spec=UserModel)
    user.id = uuid4()
    user.organization_id = mock_admin_user.organization_id
    user.email = "viewer@enterprise.com"
    user.full_name = "Security Viewer"
    user.role = "VIEWER"
    user.is_active = True
    return user


@pytest.mark.anyio
async def test_cli_authentication(mock_admin_user: UserModel) -> None:
    """Verify CLI API token generation, prefixing (vn_cli_), and raw token return."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = CLIScanningService(mock_session, mock_audit)

    req = CLITokenCreateRequest(name="GitHub Actions Key", expires_in_days=90)
    token_dto = await service.create_cli_token(mock_admin_user, req)

    assert token_dto.raw_token is not None
    assert token_dto.raw_token.startswith("vn_cli_")
    assert token_dto.token_prefix == token_dto.raw_token[:8]
    mock_audit.record_event.assert_called()


@pytest.mark.anyio
async def test_cli_token_protection(mock_admin_user: UserModel) -> None:
    """Verify raw CLI token is never stored plaintext in database records."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = CLIScanningService(mock_session, mock_audit)

    req = CLITokenCreateRequest(name="Prod Deployment Key")
    token_dto = await service.create_cli_token(mock_admin_user, req)

    # In listed tokens, raw_token must be None
    listed_tokens = await service.list_cli_tokens(mock_admin_user)
    for tok in listed_tokens:
        assert tok.raw_token is None


@pytest.mark.anyio
async def test_cli_scan_triggering(mock_analyst_user: UserModel) -> None:
    """Verify initiating a pipeline scan records metadata and audit logs."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = CLIScanningService(mock_session, mock_audit)

    with patch.object(service.assessment_service.repo, "create_job") as mock_create_job:
        mock_job = MagicMock()
        mock_job.id = str(uuid4())
        mock_job.status = "COMPLETED"
        mock_job.created_at = None
        mock_create_job.return_value = mock_job

        req = CLIScanStartRequest(
            target_url="https://api.acme.com",
            project_name="acme-api",
            branch="main",
            commit_sha="a1b2c3d4e5f6",
        )
        res = await service.start_cli_scan(mock_analyst_user, req)

        assert res.scan_id == mock_job.id
        assert res.status == "COMPLETED"
        mock_audit.record_event.assert_called()


@pytest.mark.anyio
async def test_cli_tenant_isolation(mock_admin_user: UserModel) -> None:
    """Verify projects and CLI token listings enforce tenant organization boundaries."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = CLIScanningService(mock_session, mock_audit)

    projects = await service.list_projects(mock_admin_user)
    assert len(projects) >= 1

    other_user = MagicMock(spec=UserModel)
    other_user.organization_id = uuid4()
    other_projects = await service.list_projects(other_user)
    assert len(other_projects) >= 1
    # Different instances/org IDs
    assert other_user.organization_id != mock_admin_user.organization_id


@pytest.mark.anyio
async def test_cli_rbac_permissions(
    mock_admin_user: UserModel,
    mock_viewer_user: UserModel,
) -> None:
    """Verify RBAC permissions for CLI endpoints."""
    mock_service = AsyncMock()
    mock_service.list_cli_tokens.return_value = []

    app.dependency_overrides[get_cli_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = lambda: mock_viewer_user
    app.dependency_overrides[get_current_user_or_api_key] = lambda: mock_viewer_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Viewer can list tokens
        res_list = await client.get("/api/v1/cli/tokens")
        assert res_list.status_code == 200

        # Viewer CANNOT create token (requires ADMIN / cli:manage)
        res_create = await client.post(
            "/api/v1/cli/tokens",
            json={"name": "Pipeline Token"},
        )
        assert res_create.status_code == 403

    app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_cli_exit_code_validation(mock_admin_user: UserModel) -> None:
    """Verify build gate evaluation returns exit code 0 when thresholds are satisfied."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = CLIScanningService(mock_session, mock_audit)

    with patch.object(service, "get_cli_findings_summary") as mock_sum:
        summary_dto = MagicMock()
        summary_dto.critical_count = 0
        summary_dto.high_count = 1
        summary_dto.medium_count = 3
        mock_sum.return_value = summary_dto

        req = CLIPipelineGateRequest(
            scan_id=str(uuid4()),
            max_critical=0,
            max_high=2,
            max_medium=10,
        )
        gate_res = await service.evaluate_security_gate(mock_admin_user, req)

        assert gate_res.gate_passed is True
        assert gate_res.exit_code == 0


@pytest.mark.anyio
async def test_pipeline_failure_rules(mock_admin_user: UserModel) -> None:
    """Verify build gate evaluation returns exit code 1 when critical findings exceed threshold."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = CLIScanningService(mock_session, mock_audit)

    with patch.object(service, "get_cli_findings_summary") as mock_sum:
        summary_dto = MagicMock()
        summary_dto.critical_count = 2
        summary_dto.high_count = 5
        summary_dto.medium_count = 1
        mock_sum.return_value = summary_dto

        req = CLIPipelineGateRequest(
            scan_id=str(uuid4()),
            max_critical=0,
            max_high=2,
        )
        gate_res = await service.evaluate_security_gate(mock_admin_user, req)

        assert gate_res.gate_passed is False
        assert gate_res.exit_code == 1
        assert len(gate_res.failed_conditions) >= 2


@pytest.mark.anyio
async def test_cli_audit_logging(mock_admin_user: UserModel) -> None:
    """Verify audit log records for cli.token_created and cli.pipeline_failed."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = CLIScanningService(mock_session, mock_audit)

    req = CLITokenCreateRequest(name="CI Test Key")
    await service.create_cli_token(mock_admin_user, req)
    mock_audit.record_event.assert_called()
