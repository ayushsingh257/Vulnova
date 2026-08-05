"""REST API Router for Secrets & Cryptographic Management Audit Suite."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.dependencies.rbac import require_permission
from app.application.audit_logs.services import AuditLogService
from app.application.secrets_validation.dto import (
    SecretsValidationSuiteResponse,
    SecretsValidationSummaryDTO,
)
from app.application.secrets_validation.validation_runner import (
    SecretsValidationRunnerService,
)
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/validation/secrets", tags=["Secrets & Cryptography Validation"]
)


def get_secrets_validation_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> SecretsValidationRunnerService:
    """Dependency provider for SecretsValidationRunnerService."""
    audit_log_service = AuditLogService(session)
    return SecretsValidationRunnerService(
        session=session,
        audit_log_service=audit_log_service,
    )


@router.post(
    "/run",
    response_model=SecretsValidationSuiteResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute Secrets & Cryptographic Management Suite",
    description="Executes automated in-memory Secrets scanning and cryptographic security checks across all 10 SECRET categories.",
    dependencies=[Depends(require_permission("validation:execute"))],
)
async def run_secrets_validation_suite(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[
        SecretsValidationRunnerService, Depends(get_secrets_validation_service)
    ],
) -> SecretsValidationSuiteResponse:
    """Execute secrets security validation suite."""
    return await service.run_secrets_validation(current_user)


@router.get(
    "/results",
    response_model=SecretsValidationSuiteResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Latest Secrets Security Suite Results",
    description="Returns full evaluation metrics and category assertion results for secrets and cryptography security.",
    dependencies=[Depends(require_permission("validation:read"))],
)
async def get_secrets_validation_results(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[
        SecretsValidationRunnerService, Depends(get_secrets_validation_service)
    ],
) -> SecretsValidationSuiteResponse:
    """Fetch secrets security validation suite results."""
    return await service.run_secrets_validation(current_user)


@router.get(
    "/summary",
    response_model=SecretsValidationSummaryDTO,
    status_code=status.HTTP_200_OK,
    summary="Get Secrets Security Verification Summary",
    description="Returns high-level secrets security health summary metrics and overall pass rate percentage.",
    dependencies=[Depends(require_permission("validation:read"))],
)
async def get_secrets_validation_summary(
    current_user: Annotated[UserModel, Depends(get_current_user)],
    service: Annotated[
        SecretsValidationRunnerService, Depends(get_secrets_validation_service)
    ],
) -> SecretsValidationSummaryDTO:
    """Fetch secrets security validation summary."""
    return await service.get_latest_summary(current_user)
