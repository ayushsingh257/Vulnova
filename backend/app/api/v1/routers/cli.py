"""REST API Router for CI/CD Pipeline Scanning CLI Tool."""

from typing import Annotated, List

import structlog
from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.rbac import require_permission
from app.application.audit_logs.services import AuditLogService
from app.application.cli_scanning.cli_service import CLIScanningService
from app.application.cli_scanning.dto import (
    CLIFindingSummaryDTO,
    CLIPipelineGateRequest,
    CLIPipelineGateResult,
    CLIProjectDTO,
    CLIScanStartRequest,
    CLIScanStatusResponse,
    CLITokenCreateRequest,
    CLITokenDTO,
)
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/cli", tags=["CI/CD Pipeline Scanning CLI"])


def get_cli_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> CLIScanningService:
    """Dependency provider for CLIScanningService."""
    audit_log_service = AuditLogService(session)
    return CLIScanningService(
        session=session,
        audit_log_service=audit_log_service,
    )


@router.post(
    "/tokens",
    response_model=CLITokenDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Generate CLI API Token",
    description="Generates a secure API token (prefixed with vn_cli_) for CI/CD pipeline automation.",
    dependencies=[Depends(require_permission("cli:manage"))],
)
async def create_cli_token(
    req: CLITokenCreateRequest,
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    service: Annotated[CLIScanningService, Depends(get_cli_service)],
) -> CLITokenDTO:
    """Generate CLI token."""
    return await service.create_cli_token(current_user, req)


@router.get(
    "/tokens",
    response_model=List[CLITokenDTO],
    status_code=status.HTTP_200_OK,
    summary="List Active CLI API Tokens",
    description="Returns active CLI tokens for tenant organization.",
    dependencies=[Depends(require_permission("cli:read"))],
)
async def list_cli_tokens(
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    service: Annotated[CLIScanningService, Depends(get_cli_service)],
) -> List[CLITokenDTO]:
    """List CLI tokens."""
    return await service.list_cli_tokens(current_user)


@router.delete(
    "/tokens/{token_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke CLI API Token",
    description="Revokes a CLI token preventing future pipeline authentication.",
    dependencies=[Depends(require_permission("cli:manage"))],
)
async def revoke_cli_token(
    token_id: Annotated[str, Path(description="CLI Token UUID")],
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    service: Annotated[CLIScanningService, Depends(get_cli_service)],
) -> None:
    """Revoke CLI token."""
    await service.revoke_cli_token(current_user, token_id)


@router.post(
    "/scans/start",
    response_model=CLIScanStatusResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger Pipeline Security Scan",
    description="Initiates an assessment scan job from CI/CD pipeline with branch and commit metadata.",
    dependencies=[Depends(require_permission("cli:trigger"))],
)
async def start_cli_scan(
    req: CLIScanStartRequest,
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    service: Annotated[CLIScanningService, Depends(get_cli_service)],
) -> CLIScanStatusResponse:
    """Start scan from pipeline."""
    return await service.start_cli_scan(current_user, req)


@router.get(
    "/scans/{scan_id}/status",
    response_model=CLIScanStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Pipeline Scan Status",
    description="Fetches scan status and progress percentage for CLI polling.",
    dependencies=[Depends(require_permission("cli:read"))],
)
async def get_cli_scan_status(
    scan_id: Annotated[str, Path(description="Scan Job UUID")],
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    service: Annotated[CLIScanningService, Depends(get_cli_service)],
) -> CLIScanStatusResponse:
    """Get scan status."""
    return await service.get_cli_scan_status(current_user, scan_id)


@router.get(
    "/findings/summary",
    response_model=CLIFindingSummaryDTO,
    status_code=status.HTTP_200_OK,
    summary="Get Scan Findings Summary",
    description="Returns severity count metrics for a completed pipeline scan.",
    dependencies=[Depends(require_permission("cli:read"))],
)
async def get_cli_findings_summary(
    scan_id: Annotated[str, Query(description="Scan Job UUID")],
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    service: Annotated[CLIScanningService, Depends(get_cli_service)],
) -> CLIFindingSummaryDTO:
    """Get findings summary."""
    return await service.get_cli_findings_summary(current_user, scan_id)


@router.post(
    "/gate/evaluate",
    response_model=CLIPipelineGateResult,
    status_code=status.HTTP_200_OK,
    summary="Evaluate CI/CD Pipeline Security Gate",
    description="Evaluates build security gate rules against thresholds and returns CI exit code.",
    dependencies=[Depends(require_permission("cli:read"))],
)
async def evaluate_security_gate(
    req: CLIPipelineGateRequest,
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    service: Annotated[CLIScanningService, Depends(get_cli_service)],
) -> CLIPipelineGateResult:
    """Evaluate pipeline security gate."""
    return await service.evaluate_security_gate(current_user, req)


@router.get(
    "/projects",
    response_model=List[CLIProjectDTO],
    status_code=status.HTTP_200_OK,
    summary="List Registered Projects & Repositories",
    description="Returns registered projects and repositories for tenant.",
    dependencies=[Depends(require_permission("cli:read"))],
)
async def list_projects(
    current_user: Annotated[UserModel, Depends(get_current_user_or_api_key)],
    service: Annotated[CLIScanningService, Depends(get_cli_service)],
) -> List[CLIProjectDTO]:
    """List projects."""
    return await service.list_projects(current_user)
