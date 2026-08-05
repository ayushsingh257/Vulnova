"""REST API Router for Enterprise Jira & GitHub Issues Integrations."""

from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.rbac import require_permission
from app.application.audit_logs.services import AuditLogService
from app.application.integrations.dto import (
    CreateIssueRequest,
    ExternalIssueDTO,
    GitHubConfigDTO,
    IntegrationConfigResponse,
    JiraConfigDTO,
    SaveGitHubConfigRequest,
    SaveJiraConfigRequest,
    SyncStatusResponse,
)
from app.application.integrations.integration_service import IntegrationService
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/integrations", tags=["Enterprise Integrations"])


def get_integration_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> IntegrationService:
    """Dependency provider for IntegrationService."""
    audit_log_service = AuditLogService(session)
    return IntegrationService(
        session=session,
        audit_log_service=audit_log_service,
    )


@router.get(
    "",
    response_model=IntegrationConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Integration Configuration Status",
    description="Returns configuration status for Jira Cloud and GitHub Issues integrations (secrets masked).",
    dependencies=[Depends(require_permission("integrations:read"))],
)
async def get_integration_status(
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> IntegrationConfigResponse:
    """Get integration configurations for organization."""
    return await service.get_integration_status(current_user)


@router.post(
    "/jira/config",
    response_model=JiraConfigDTO,
    status_code=status.HTTP_200_OK,
    summary="Save Jira Cloud Integration Configuration",
    description="Encrypts Jira API token and persists configuration for tenant.",
    dependencies=[Depends(require_permission("integrations:manage"))],
)
async def save_jira_config(
    req: SaveJiraConfigRequest,
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> JiraConfigDTO:
    """Configure Jira integration."""
    return await service.save_jira_config(current_user, req)


@router.post(
    "/github/config",
    response_model=GitHubConfigDTO,
    status_code=status.HTTP_200_OK,
    summary="Save GitHub Issues Integration Configuration",
    description="Encrypts GitHub Personal Access Token and persists configuration for tenant.",
    dependencies=[Depends(require_permission("integrations:manage"))],
)
async def save_github_config(
    req: SaveGitHubConfigRequest,
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> GitHubConfigDTO:
    """Configure GitHub integration."""
    return await service.save_github_config(current_user, req)


@router.post(
    "/jira/issues/{finding_id}",
    response_model=ExternalIssueDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create Jira Ticket for Vulnerability Finding",
    description="Formats finding details and creates a ticket in connected Jira project.",
    dependencies=[Depends(require_permission("integrations:create"))],
)
async def create_jira_issue(
    finding_id: Annotated[UUID, Path(description="Vulnerability Finding UUID")],
    req: CreateIssueRequest,
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> ExternalIssueDTO:
    """Create Jira issue for finding."""
    return await service.create_jira_issue(current_user, finding_id, req)


@router.post(
    "/github/issues/{finding_id}",
    response_model=ExternalIssueDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create GitHub Issue for Vulnerability Finding",
    description="Formats finding details into Markdown and creates an issue in target GitHub repository.",
    dependencies=[Depends(require_permission("integrations:create"))],
)
async def create_github_issue(
    finding_id: Annotated[UUID, Path(description="Vulnerability Finding UUID")],
    req: CreateIssueRequest,
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> ExternalIssueDTO:
    """Create GitHub issue for finding."""
    return await service.create_github_issue(current_user, finding_id, req)


@router.post(
    "/jira/{finding_id}/{issue_key}/sync",
    response_model=SyncStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Sync Jira Issue Lifecycle Status",
    description="Fetches Jira status and maps changes through controlled state transition layer into Vulnova finding state.",
    dependencies=[Depends(require_permission("integrations:update"))],
)
async def sync_jira_status(
    finding_id: Annotated[UUID, Path(description="Vulnerability Finding UUID")],
    issue_key: Annotated[str, Path(description="Jira Issue Key, e.g., SEC-101")],
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> SyncStatusResponse:
    """Sync Jira ticket status."""
    return await service.sync_jira_status(current_user, finding_id, issue_key)


@router.post(
    "/github/{finding_id}/{issue_number}/sync",
    response_model=SyncStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Sync GitHub Issue Lifecycle Status",
    description="Fetches GitHub issue state and maps changes through controlled state transition layer into Vulnova finding state.",
    dependencies=[Depends(require_permission("integrations:update"))],
)
async def sync_github_status(
    finding_id: Annotated[UUID, Path(description="Vulnerability Finding UUID")],
    issue_number: Annotated[str, Path(description="GitHub Issue Number, e.g., 42")],
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    service: Annotated[IntegrationService, Depends(get_integration_service)],
) -> SyncStatusResponse:
    """Sync GitHub issue status."""
    return await service.sync_github_status(current_user, finding_id, issue_number)
