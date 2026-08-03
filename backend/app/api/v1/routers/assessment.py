"""FastAPI Router for Vulnerability Assessment Engine (/api/v1/assessments & /api/v1/findings)."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.rbac import require_permission
from app.application.assessment.dto import (
    AssessmentJobResponse,
    CreateAssessmentRequest,
    FindingDTO,
    PluginMetadataDTO,
    ScanProfileDTO,
)
from app.application.assessment.services import AssessmentService
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

router = APIRouter(tags=["Vulnerability Assessment Engine & Dynamic Testing"])


@router.post(
    "/assessments",
    response_model=AssessmentJobResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("scans:trigger"))],
)
async def create_and_run_assessment(
    req: CreateAssessmentRequest,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> AssessmentJobResponse:
    """Trigger a vulnerability assessment scan on a target web asset.

    Requires authentication and 'scans:trigger' RBAC permission. Enforces SSRF target validation.
    """
    service = AssessmentService(session)
    return await service.create_and_run_assessment(req, current_user)


@router.get(
    "/assessments/profiles",
    response_model=List[ScanProfileDTO],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("scans:read"))],
)
async def list_scan_profiles(
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> List[ScanProfileDTO]:
    """List all available enterprise scan profiles and default execution policies.

    Requires authentication and 'scans:read' RBAC permission.
    """
    service = AssessmentService(session)
    return service.list_scan_profiles()


@router.get(
    "/assessments/plugins",
    response_model=List[PluginMetadataDTO],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("scans:read"))],
)
async def list_registered_plugins(
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> List[PluginMetadataDTO]:
    """List metadata for all registered security assessment plugins.

    Requires authentication and 'scans:read' RBAC permission.
    """
    service = AssessmentService(session)
    return service.list_registered_plugins()


@router.get(
    "/assessments/{assessment_id}",
    response_model=AssessmentJobResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("scans:read"))],
)
async def get_assessment_job(
    assessment_id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> AssessmentJobResponse:
    """Retrieve details and findings for a specific assessment job.

    Requires authentication and 'scans:read' RBAC permission. Enforces multi-tenant isolation.
    """
    service = AssessmentService(session)
    return await service.get_assessment_job(assessment_id, current_user)


@router.get(
    "/findings",
    response_model=List[FindingDTO],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("findings:read"))],
)
async def list_findings(
    severity: Optional[str] = Query(
        None, description="Optional severity filter (e.g. HIGH, CRITICAL)"
    ),
    category: Optional[str] = Query(
        None, description="Optional vulnerability category filter"
    ),
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> List[FindingDTO]:
    """List discovered security findings for the authenticated organization.

    Requires authentication and 'findings:read' RBAC permission. Supports severity and category filters.
    """
    service = AssessmentService(session)
    return await service.list_findings(
        current_user, severity=severity, category=category
    )
