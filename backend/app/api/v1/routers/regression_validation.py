"""REST API Router for Automated Security Regression Testing Framework."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.dependencies.rbac import require_permission
from app.application.audit_logs.services import AuditLogService
from app.application.regression_validation.dto import (
    RegressionValidationSuiteResponse,
    RegressionValidationSummaryDTO,
)
from app.application.regression_validation.validation_runner import (
    RegressionValidationRunnerService,
)
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/validation/regression", tags=["Automated Security Regression Validation"]
)


def get_regression_validation_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> RegressionValidationRunnerService:
    """Dependency provider for RegressionValidationRunnerService."""
    audit_log_service = AuditLogService(session)
    return RegressionValidationRunnerService(
        session=session,
        audit_log_service=audit_log_service,
    )


@router.post(
    "/run",
    response_model=RegressionValidationSuiteResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Automated Security Regression Testing Suite",
    description="Executes automated in-memory security regression checks across all 10 Security Regression categories (REGRESSION1 - REGRESSION10).",
    dependencies=[Depends(require_permission("validation:execute"))],
)
async def run_regression_validation_suite(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[
        RegressionValidationRunnerService, Depends(get_regression_validation_service)
    ],
) -> RegressionValidationSuiteResponse:
    """Execute security regression validation suite."""
    return await service.run_regression_validation(current_user)


@router.get(
    "/results",
    response_model=RegressionValidationSuiteResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Latest Security Regression Suite Results",
    description="Returns full evaluation metrics and category assertion results for security regression testing.",
    dependencies=[Depends(require_permission("validation:read"))],
)
async def get_regression_validation_results(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[
        RegressionValidationRunnerService, Depends(get_regression_validation_service)
    ],
) -> RegressionValidationSuiteResponse:
    """Fetch security regression validation suite results."""
    return await service.run_regression_validation(current_user)


@router.get(
    "/summary",
    response_model=RegressionValidationSummaryDTO,
    status_code=status.HTTP_200_OK,
    summary="Get Security Regression Verification Summary",
    description="Returns high-level security regression health summary metrics and overall pass rate percentage.",
    dependencies=[Depends(require_permission("validation:read"))],
)
async def get_regression_validation_summary(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[
        RegressionValidationRunnerService, Depends(get_regression_validation_service)
    ],
) -> RegressionValidationSummaryDTO:
    """Fetch security regression validation summary."""
    return await service.get_latest_summary(current_user)
