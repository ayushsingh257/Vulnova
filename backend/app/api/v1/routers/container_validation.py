"""REST API Router for Container Image Security Audit & Runtime Hardening Suite."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.dependencies.rbac import require_permission
from app.application.audit_logs.services import AuditLogService
from app.application.container_validation.dto import (
    ContainerValidationSuiteResponse,
    ContainerValidationSummaryDTO,
)
from app.application.container_validation.validation_runner import (
    ContainerValidationRunnerService,
)
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/validation/container", tags=["Container Security Validation"]
)


def get_container_validation_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ContainerValidationRunnerService:
    """Dependency provider for ContainerValidationRunnerService."""
    audit_log_service = AuditLogService(session)
    return ContainerValidationRunnerService(
        session=session,
        audit_log_service=audit_log_service,
    )


@router.post(
    "/run",
    response_model=ContainerValidationSuiteResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Container Image Security & Hardening Suite",
    description="Executes automated in-memory Container security and runtime hardening checks across all 10 CONTAINER categories.",
    dependencies=[Depends(require_permission("validation:execute"))],
)
async def run_container_validation_suite(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[
        ContainerValidationRunnerService, Depends(get_container_validation_service)
    ],
) -> ContainerValidationSuiteResponse:
    """Execute container security validation suite."""
    return await service.run_container_validation(current_user)


@router.get(
    "/results",
    response_model=ContainerValidationSuiteResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Latest Container Security Suite Results",
    description="Returns full evaluation metrics and category assertion results for container security.",
    dependencies=[Depends(require_permission("validation:read"))],
)
async def get_container_validation_results(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[
        ContainerValidationRunnerService, Depends(get_container_validation_service)
    ],
) -> ContainerValidationSuiteResponse:
    """Fetch container security validation suite results."""
    return await service.run_container_validation(current_user)


@router.get(
    "/summary",
    response_model=ContainerValidationSummaryDTO,
    status_code=status.HTTP_200_OK,
    summary="Get Container Security Verification Summary",
    description="Returns high-level container security health summary metrics and overall pass rate percentage.",
    dependencies=[Depends(require_permission("validation:read"))],
)
async def get_container_validation_summary(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[
        ContainerValidationRunnerService, Depends(get_container_validation_service)
    ],
) -> ContainerValidationSummaryDTO:
    """Fetch container security validation summary."""
    return await service.get_latest_summary(current_user)
