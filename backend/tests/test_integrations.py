"""Unit and Integration Test Suite for Enterprise Jira & GitHub Issues Integrations."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.routers.integrations import get_integration_service
from app.application.integrations.github.github_mapper import (
    ControlledGitHubStatusMapper,
)
from app.application.integrations.integration_service import IntegrationService
from app.application.integrations.jira.jira_mapper import ControlledJiraStatusMapper
from app.infrastructure.database.models.assessment import SecurityFindingModel
from app.infrastructure.database.models.user import UserModel
from app.main import app
from app.security.encryption import SecretEncryptionService


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


def create_mock_finding(organization_id: Any) -> MagicMock:
    finding = MagicMock(spec=SecurityFindingModel)
    finding.id = uuid4()
    finding.organization_id = organization_id
    finding.title = "SQL Injection in Payment Gateway"
    finding.severity = "CRITICAL"
    finding.category = "SQL Injection"
    finding.risk_score = 9.8
    finding.cve_id = "CVE-2024-8888"
    finding.cwe_id = "CWE-89"
    finding.description = "Unsanitized user payload passed directly to SQL query."
    finding.remediation = "Use parameterized queries."
    finding.status = "CONFIRMED"
    finding.evidence_json = {}
    return finding


def test_controlled_status_mappers() -> None:
    """Verify controlled state transition layer for Jira & GitHub status sync."""
    # Jira transitions
    assert (
        ControlledJiraStatusMapper.map_jira_status_to_vulnova_state("Done", "CONFIRMED")
        == "RESOLVED"
    )
    assert (
        ControlledJiraStatusMapper.map_jira_status_to_vulnova_state(
            "In Progress", "CONFIRMED"
        )
        == "IN_REMEDIATION"
    )
    assert (
        ControlledJiraStatusMapper.map_jira_status_to_vulnova_state(
            "To Do", "IN_REMEDIATION"
        )
        == "CONFIRMED"
    )

    # GitHub transitions
    assert (
        ControlledGitHubStatusMapper.map_github_status_to_vulnova_state(
            "closed", [], "CONFIRMED"
        )
        == "RESOLVED"
    )
    assert (
        ControlledGitHubStatusMapper.map_github_status_to_vulnova_state(
            "open", ["in-progress"], "CONFIRMED"
        )
        == "IN_REMEDIATION"
    )
    assert (
        ControlledGitHubStatusMapper.map_github_status_to_vulnova_state(
            "open", [], "IN_REMEDIATION"
        )
        == "CONFIRMED"
    )


def test_secret_protection() -> None:
    """Verify secrets encryption using SecretEncryptionService."""
    enc = SecretEncryptionService()
    secret = "ghp_super_secret_github_token_12345"
    encrypted = enc.encrypt_secret(secret)

    assert encrypted != secret
    assert enc.decrypt_secret(encrypted) == secret


@pytest.mark.anyio
async def test_jira_issue_creation(
    mock_admin_user: UserModel, mock_analyst_user: UserModel
) -> None:
    """Verify Jira ticket creation with mock JiraClient."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = IntegrationService(mock_session, mock_audit)

    # Configure Jira first
    jira_req = MagicMock(
        host_url="acme.atlassian.net",
        email="jira@acme.com",
        api_token="secret_token_123",
        project_key="SEC",
        issue_type="Bug",
    )
    await service.save_jira_config(mock_admin_user, jira_req)

    finding = create_mock_finding(mock_admin_user.organization_id)
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = finding
    mock_session.execute.return_value = mock_res

    with patch(
        "app.application.integrations.integration_service.JiraClient"
    ) as MockJiraClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.create_issue.return_value = {
            "issue_id": "10001",
            "issue_key": "SEC-42",
            "issue_url": "https://acme.atlassian.net/browse/SEC-42",
        }
        MockJiraClient.return_value = mock_client_instance

        create_req = MagicMock(custom_labels=["p1"], assignee=None)
        res = await service.create_jira_issue(mock_analyst_user, finding.id, create_req)

        assert res.issue_key == "SEC-42"
        assert res.provider == "jira"
        mock_audit.record_event.assert_called()


@pytest.mark.anyio
async def test_github_issue_creation(
    mock_admin_user: UserModel, mock_analyst_user: UserModel
) -> None:
    """Verify GitHub issue creation with mock GitHubClient."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = IntegrationService(mock_session, mock_audit)

    # Configure GitHub first
    gh_req = MagicMock(
        repo_owner="acme-corp",
        repo_name="payments-api",
        personal_access_token="ghp_secret_pat_999",
    )
    await service.save_github_config(mock_admin_user, gh_req)

    finding = create_mock_finding(mock_admin_user.organization_id)
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = finding
    mock_session.execute.return_value = mock_res

    with patch(
        "app.application.integrations.integration_service.GitHubClient"
    ) as MockGHClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.create_issue.return_value = {
            "issue_id": "987654",
            "issue_key": "#15",
            "issue_number": "15",
            "issue_url": "https://github.com/acme-corp/payments-api/issues/15",
        }
        MockGHClient.return_value = mock_client_instance

        create_req = MagicMock(custom_labels=["urgent"], assignee=None)
        res = await service.create_github_issue(
            mock_analyst_user, finding.id, create_req
        )

        assert res.issue_key == "#15"
        assert res.provider == "github"
        mock_audit.record_event.assert_called()


@pytest.mark.anyio
async def test_status_sync(
    mock_admin_user: UserModel, mock_analyst_user: UserModel
) -> None:
    """Verify GitHub issue status sync through controlled status mapper."""
    mock_session = AsyncMock()
    mock_audit = AsyncMock()
    service = IntegrationService(mock_session, mock_audit)

    gh_req = MagicMock(
        repo_owner="acme-corp",
        repo_name="payments-api",
        personal_access_token="ghp_secret_pat_999",
    )
    await service.save_github_config(mock_admin_user, gh_req)

    finding = create_mock_finding(mock_admin_user.organization_id)
    finding.status = "CONFIRMED"

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = finding
    mock_session.execute.return_value = mock_res

    with patch(
        "app.application.integrations.integration_service.GitHubClient"
    ) as MockGHClient:
        mock_client_instance = AsyncMock()
        mock_client_instance.get_issue.return_value = {
            "issue_number": "15",
            "state": "closed",
            "labels": [],
        }
        MockGHClient.return_value = mock_client_instance

        sync_res = await service.sync_github_status(mock_analyst_user, finding.id, "15")

        assert sync_res.previous_vulnova_status == "CONFIRMED"
        assert sync_res.updated_vulnova_status == "RESOLVED"
        assert sync_res.provider == "github"
        assert sync_res.external_status == "closed"


@pytest.mark.anyio
async def test_rbac_permissions(
    mock_admin_user: UserModel,
    mock_analyst_user: UserModel,
    mock_viewer_user: UserModel,
) -> None:
    """Verify RBAC permission enforcement for integration endpoints."""
    mock_service = AsyncMock()
    mock_service.get_integration_status.return_value = {
        "jira": {"is_configured": False},
        "github": {"is_configured": False},
    }

    app.dependency_overrides[get_integration_service] = lambda: mock_service
    app.dependency_overrides[get_current_user] = lambda: mock_viewer_user
    app.dependency_overrides[get_current_user_or_api_key] = lambda: mock_viewer_user

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        # Viewer can read integration status
        res = await client.get("/api/v1/integrations")
        assert res.status_code == 200

        # Viewer CANNOT save configuration (requires ADMIN / integrations:manage)
        res_config = await client.post("/api/v1/integrations/jira/config", json={})
        assert res_config.status_code == 403

        # Switch to Admin
        app.dependency_overrides[get_current_user] = lambda: mock_admin_user
        app.dependency_overrides[get_current_user_or_api_key] = lambda: mock_admin_user
        mock_service.save_jira_config.return_value = {"is_configured": True}
        res_admin_config = await client.post(
            "/api/v1/integrations/jira/config",
            json={
                "host_url": "acme.atlassian.net",
                "email": "a@acme.com",
                "api_token": "tok",
                "project_key": "SEC",
            },
        )
        assert res_admin_config.status_code == 200

    app.dependency_overrides.clear()
