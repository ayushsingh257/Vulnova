"""REST API Router for Dependency Security Audit & SCA Enforcement Suite."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.dependencies.rbac import require_permission
from app.application.audit_logs.services import AuditLogService
from app.application.sca_validation.dto import (
    SCAValidationSuiteResponse,
    SCAValidationSummaryDTO,
)
from app.application.sca_validation.validation_runner import (
    SCAValidationRunnerService,
)
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/validation/sca", tags=["Dependency Security Validation"])


def get_sca_validation_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> SCAValidationRunnerService:
    """Dependency provider for SCAValidationRunnerService."""
    audit_log_service = AuditLogService(session)
    return SCAValidationRunnerService(
        session=session,
        audit_log_service=audit_log_service,
    )


@router.post(
    "/run",
    response_model=SCAValidationSuiteResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Dependency Security & SCA Enforcement Suite",
    description="Executes automated in-memory Software Composition Analysis checks across all 10 SCA categories.",
    dependencies=[Depends(require_permission("validation:execute"))],
)
async def run_sca_validation_suite(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[SCAValidationRunnerService, Depends(get_sca_validation_service)],
) -> SCAValidationSuiteResponse:
    """Execute dependency security validation suite."""
    return await service.run_sca_validation(current_user)


@router.get(
    "/results",
    response_model=SCAValidationSuiteResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Latest Dependency Security Suite Results",
    description="Returns full evaluation metrics and category assertion results for dependency security.",
    dependencies=[Depends(require_permission("validation:read"))],
)
async def get_sca_validation_results(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[SCAValidationRunnerService, Depends(get_sca_validation_service)],
) -> SCAValidationSuiteResponse:
    """Fetch dependency security validation suite results."""
    return await service.run_sca_validation(current_user)


@router.get(
    "/summary",
    response_model=SCAValidationSummaryDTO,
    status_code=status.HTTP_200_OK,
    summary="Get Dependency Security Verification Summary",
    description="Returns high-level dependency security health summary metrics and overall pass rate percentage.",
    dependencies=[Depends(require_permission("validation:read"))],
)
async def get_sca_validation_summary(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[SCAValidationRunnerService, Depends(get_sca_validation_service)],
) -> SCAValidationSummaryDTO:
    """Fetch dependency security validation summary."""
    return await service.get_latest_summary(current_user)
