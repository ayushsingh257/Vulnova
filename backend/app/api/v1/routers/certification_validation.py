"""REST API Router for Security Control Plane Final Certification & Compliance Readiness Suite."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.dependencies.rbac import require_permission
from app.application.audit_logs.services import AuditLogService
from app.application.certification_validation.dto import (
    CertificationValidationSuiteResponse,
    CertificationValidationSummaryDTO,
)
from app.application.certification_validation.validation_runner import (
    CertificationValidationRunnerService,
)
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/validation/certification",
    tags=["Security Control Plane Final Certification"],
)


def get_certification_validation_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> CertificationValidationRunnerService:
    """Dependency provider for CertificationValidationRunnerService."""
    audit_log_service = AuditLogService(session)
    return CertificationValidationRunnerService(
        session=session,
        audit_log_service=audit_log_service,
    )


@router.post(
    "/run",
    response_model=CertificationValidationSuiteResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Final Security Control Plane Certification",
    description="Executes automated in-memory security certification checks across all 10 Security Control Plane categories (CERTIFICATION1 - CERTIFICATION10).",
    dependencies=[Depends(require_permission("validation:execute"))],
)
async def run_certification_validation_suite(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[
        CertificationValidationRunnerService,
        Depends(get_certification_validation_service),
    ],
) -> CertificationValidationSuiteResponse:
    """Execute security certification validation suite."""
    return await service.run_certification_validation(current_user)


@router.get(
    "/results",
    response_model=CertificationValidationSuiteResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Security Certification Results",
    description="Returns full evaluation metrics and category assertion results for enterprise security control plane certification.",
    dependencies=[Depends(require_permission("validation:read"))],
)
async def get_certification_validation_results(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[
        CertificationValidationRunnerService,
        Depends(get_certification_validation_service),
    ],
) -> CertificationValidationSuiteResponse:
    """Fetch security certification validation suite results."""
    return await service.run_certification_validation(current_user)


@router.get(
    "/summary",
    response_model=CertificationValidationSummaryDTO,
    status_code=status.HTTP_200_OK,
    summary="Get Security Certification Summary",
    description="Returns high-level enterprise security certification summary metrics and overall certification score percentage.",
    dependencies=[Depends(require_permission("validation:read"))],
)
async def get_certification_validation_summary(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[
        CertificationValidationRunnerService,
        Depends(get_certification_validation_service),
    ],
) -> CertificationValidationSummaryDTO:
    """Fetch security certification validation summary."""
    return await service.get_latest_summary(current_user)
