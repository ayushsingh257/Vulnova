"""REST API Router for OWASP Top 10 (2021) Security Validation Suite."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.dependencies.rbac import require_permission
from app.application.audit_logs.services import AuditLogService
from app.application.owasp_validation.dto import (
    OWASPValidationSuiteResponse,
    OWASPVerificationSummaryDTO,
)
from app.application.owasp_validation.validation_runner import (
    OWASPValidationRunnerService,
)
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/validation/owasp-top-10", tags=["OWASP Security Validation"]
)


def get_validation_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> OWASPValidationRunnerService:
    """Dependency provider for OWASPValidationRunnerService."""
    audit_log_service = AuditLogService(session)
    return OWASPValidationRunnerService(
        session=session,
        audit_log_service=audit_log_service,
    )


@router.post(
    "/run",
    response_model=OWASPValidationSuiteResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute OWASP Top 10 Security Validation Suite",
    description="Executes automated in-memory security assertion checks across all 10 OWASP Top 10 (2021) categories.",
    dependencies=[Depends(require_permission("validation:execute"))],
)
async def run_owasp_validation_suite(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[OWASPValidationRunnerService, Depends(get_validation_service)],
) -> OWASPValidationSuiteResponse:
    """Execute OWASP Top 10 validation suite."""
    return await service.run_validation_suite(current_user)


@router.get(
    "/results",
    response_model=OWASPValidationSuiteResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Latest OWASP Top 10 Validation Suite Results",
    description="Returns full evaluation metrics and category assertion results.",
    dependencies=[Depends(require_permission("validation:read"))],
)
async def get_owasp_validation_results(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[OWASPValidationRunnerService, Depends(get_validation_service)],
) -> OWASPValidationSuiteResponse:
    """Fetch OWASP validation suite results."""
    return await service.run_validation_suite(current_user)


@router.get(
    "/summary",
    response_model=OWASPVerificationSummaryDTO,
    status_code=status.HTTP_200_OK,
    summary="Get OWASP Top 10 Verification Summary",
    description="Returns high-level health summary metrics and overall pass rate percentage.",
    dependencies=[Depends(require_permission("validation:read"))],
)
async def get_owasp_validation_summary(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[OWASPValidationRunnerService, Depends(get_validation_service)],
) -> OWASPVerificationSummaryDTO:
    """Fetch OWASP validation summary."""
    return await service.get_latest_summary(current_user)
