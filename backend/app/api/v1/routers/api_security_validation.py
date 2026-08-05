"""REST API Router for OWASP API Security Top 10 (2023) Validation Suite."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.dependencies.rbac import require_permission
from app.application.api_security_validation.dto import (
    APIValidationSuiteResponse,
    APIValidationSummaryDTO,
)
from app.application.api_security_validation.validation_runner import (
    APISecurityValidationRunnerService,
)
from app.application.audit_logs.services import AuditLogService
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/validation/api-security", tags=["API Security Validation"])


def get_api_validation_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> APISecurityValidationRunnerService:
    """Dependency provider for APISecurityValidationRunnerService."""
    audit_log_service = AuditLogService(session)
    return APISecurityValidationRunnerService(
        session=session,
        audit_log_service=audit_log_service,
    )


@router.post(
    "/run",
    response_model=APIValidationSuiteResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute OWASP API Security Top 10 Validation Suite",
    description="Executes automated in-memory API security assertion checks across all 10 OWASP API Security Top 10 (2023) categories.",
    dependencies=[Depends(require_permission("validation:execute"))],
)
async def run_api_security_validation_suite(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[
        APISecurityValidationRunnerService, Depends(get_api_validation_service)
    ],
) -> APIValidationSuiteResponse:
    """Execute API security validation suite."""
    return await service.run_api_security_validation(current_user)


@router.get(
    "/results",
    response_model=APIValidationSuiteResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Latest OWASP API Security Validation Suite Results",
    description="Returns full evaluation metrics and category assertion results for API security.",
    dependencies=[Depends(require_permission("validation:read"))],
)
async def get_api_security_validation_results(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[
        APISecurityValidationRunnerService, Depends(get_api_validation_service)
    ],
) -> APIValidationSuiteResponse:
    """Fetch API security validation suite results."""
    return await service.run_api_security_validation(current_user)


@router.get(
    "/summary",
    response_model=APIValidationSummaryDTO,
    status_code=status.HTTP_200_OK,
    summary="Get OWASP API Security Verification Summary",
    description="Returns high-level API health summary metrics and overall pass rate percentage.",
    dependencies=[Depends(require_permission("validation:read"))],
)
async def get_api_security_validation_summary(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[
        APISecurityValidationRunnerService, Depends(get_api_validation_service)
    ],
) -> APIValidationSummaryDTO:
    """Fetch API security validation summary."""
    return await service.get_latest_summary(current_user)
