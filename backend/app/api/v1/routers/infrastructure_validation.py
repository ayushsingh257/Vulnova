"""REST API Router for Security Configuration & Infrastructure Validation Suite."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.dependencies.rbac import require_permission
from app.application.audit_logs.services import AuditLogService
from app.application.infrastructure_validation.dto import (
    InfrastructureValidationSuiteResponse,
    InfrastructureValidationSummaryDTO,
)
from app.application.infrastructure_validation.validation_runner import (
    InfrastructureSecurityValidationRunnerService,
)
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/validation/infrastructure", tags=["Infrastructure Validation"]
)


def get_infra_validation_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> InfrastructureSecurityValidationRunnerService:
    """Dependency provider for InfrastructureSecurityValidationRunnerService."""
    audit_log_service = AuditLogService(session)
    return InfrastructureSecurityValidationRunnerService(
        session=session,
        audit_log_service=audit_log_service,
    )


@router.post(
    "/run",
    response_model=InfrastructureValidationSuiteResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Infrastructure Security Validation Suite",
    description="Executes automated in-memory infrastructure security assertion checks across all 10 INFRA categories.",
    dependencies=[Depends(require_permission("validation:execute"))],
)
async def run_infrastructure_validation_suite(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[
        InfrastructureSecurityValidationRunnerService,
        Depends(get_infra_validation_service),
    ],
) -> InfrastructureValidationSuiteResponse:
    """Execute infrastructure security validation suite."""
    return await service.run_infrastructure_validation(current_user)


@router.get(
    "/results",
    response_model=InfrastructureValidationSuiteResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Latest Infrastructure Security Validation Suite Results",
    description="Returns full evaluation metrics and category assertion results for infrastructure security.",
    dependencies=[Depends(require_permission("validation:read"))],
)
async def get_infrastructure_validation_results(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[
        InfrastructureSecurityValidationRunnerService,
        Depends(get_infra_validation_service),
    ],
) -> InfrastructureValidationSuiteResponse:
    """Fetch infrastructure security validation suite results."""
    return await service.run_infrastructure_validation(current_user)


@router.get(
    "/summary",
    response_model=InfrastructureValidationSummaryDTO,
    status_code=status.HTTP_200_OK,
    summary="Get Infrastructure Security Verification Summary",
    description="Returns high-level infrastructure security health summary metrics and overall pass rate percentage.",
    dependencies=[Depends(require_permission("validation:read"))],
)
async def get_infrastructure_validation_summary(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[
        InfrastructureSecurityValidationRunnerService,
        Depends(get_infra_validation_service),
    ],
) -> InfrastructureValidationSummaryDTO:
    """Fetch infrastructure security validation summary."""
    return await service.get_latest_summary(current_user)
