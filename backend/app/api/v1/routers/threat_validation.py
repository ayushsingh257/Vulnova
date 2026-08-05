"""REST API Router for Threat Model Review & STRIDE Verification Suite."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.dependencies.rbac import require_permission
from app.application.audit_logs.services import AuditLogService
from app.application.threat_validation.dto import (
    ThreatValidationSuiteResponse,
    ThreatValidationSummaryDTO,
)
from app.application.threat_validation.validation_runner import (
    ThreatValidationRunnerService,
)
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/validation/threat", tags=["Threat Model & STRIDE Validation"]
)


def get_threat_validation_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ThreatValidationRunnerService:
    """Dependency provider for ThreatValidationRunnerService."""
    audit_log_service = AuditLogService(session)
    return ThreatValidationRunnerService(
        session=session,
        audit_log_service=audit_log_service,
    )


@router.post(
    "/run",
    response_model=ThreatValidationSuiteResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Threat Model Review & STRIDE Verification Suite",
    description="Executes automated in-memory threat model checks across all 10 STRIDE categories (STRIDE1 - STRIDE10).",
    dependencies=[Depends(require_permission("validation:execute"))],
)
async def run_threat_validation_suite(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[
        ThreatValidationRunnerService, Depends(get_threat_validation_service)
    ],
) -> ThreatValidationSuiteResponse:
    """Execute threat validation suite."""
    return await service.run_threat_validation(current_user)


@router.get(
    "/results",
    response_model=ThreatValidationSuiteResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Latest Threat Model Suite Results",
    description="Returns full evaluation metrics and category assertion results for STRIDE threat model verification.",
    dependencies=[Depends(require_permission("validation:read"))],
)
async def get_threat_validation_results(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[
        ThreatValidationRunnerService, Depends(get_threat_validation_service)
    ],
) -> ThreatValidationSuiteResponse:
    """Fetch threat validation suite results."""
    return await service.run_threat_validation(current_user)


@router.get(
    "/summary",
    response_model=ThreatValidationSummaryDTO,
    status_code=status.HTTP_200_OK,
    summary="Get Threat Model Verification Summary",
    description="Returns high-level threat model security health summary metrics and overall pass rate percentage.",
    dependencies=[Depends(require_permission("validation:read"))],
)
async def get_threat_validation_summary(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[
        ThreatValidationRunnerService, Depends(get_threat_validation_service)
    ],
) -> ThreatValidationSummaryDTO:
    """Fetch threat validation summary."""
    return await service.get_latest_summary(current_user)
