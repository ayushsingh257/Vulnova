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
    ScanLifecycleStateDTO,
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


# ── Phase 6.3: Scan Execution Lifecycle & Retry Endpoints ──


@router.get(
    "/assessments/{assessment_id}/state",
    response_model=ScanLifecycleStateDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("scans:read"))],
)
async def get_scan_lifecycle_state(
    assessment_id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> ScanLifecycleStateDTO:
    """Retrieve detailed state machine status, step, and retry metrics for a scan job.

    Requires authentication and 'scans:read' RBAC permission.
    """
    from app.core.exceptions import ResourceNotFoundException
    from app.infrastructure.database.repositories.assessment_repository import (
        AssessmentRepository,
    )

    repo = AssessmentRepository(session)
    job = await repo.get_job_by_id(current_user.organization_id, assessment_id)
    if job is None:
        raise ResourceNotFoundException(
            f"Assessment job '{assessment_id}' not found in organization."
        )

    exec_state = job.execution_state or "QUEUED"
    is_term = exec_state in ("COMPLETED", "FAILED", "CANCELLED")

    return ScanLifecycleStateDTO(
        job_id=str(job.id),
        organization_id=str(job.organization_id),
        target_url=job.target_url,
        execution_state=exec_state,
        status=job.status,
        current_step=job.current_step,
        retry_count=job.retry_count,
        max_retries=job.max_retries,
        last_error=job.last_error,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        is_terminal=is_term,
    )


@router.post(
    "/assessments/{assessment_id}/retry",
    response_model=AssessmentJobResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("scans:retry"))],
)
async def retry_assessment_job(
    assessment_id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> AssessmentJobResponse:
    """Manually trigger retry for a failed or cancelled assessment job.

    Requires authentication and 'scans:retry' RBAC permission.
    """
    from app.application.assessment.scan_lifecycle_manager import (
        ScanLifecycleManagerService,
    )
    from app.domain.entities.scan_lifecycle import ScanExecutionState

    manager = ScanLifecycleManagerService(session)
    await manager.transition_state(
        organization_id=current_user.organization_id,
        job_id=assessment_id,
        target_state=ScanExecutionState.QUEUED,
        current_step="Manual Retry Triggered",
        actor_id=current_user.id,
    )
    await session.commit()
    service = AssessmentService(session)
    return await service.get_assessment_job(assessment_id, current_user)


@router.post(
    "/assessments/{assessment_id}/cancel",
    response_model=AssessmentJobResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("scans:cancel"))],
)
async def cancel_assessment_job(
    assessment_id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> AssessmentJobResponse:
    """Signal abort and transition active assessment job to CANCELLED.

    Requires authentication and 'scans:cancel' RBAC permission. Releases target locks.
    """
    from app.application.assessment.scan_lifecycle_manager import (
        ScanLifecycleManagerService,
    )

    manager = ScanLifecycleManagerService(session)
    await manager.handle_scan_cancellation(
        organization_id=current_user.organization_id,
        job_id=assessment_id,
        cancelled_by=current_user.id,
        reason=f"Scan job cancelled by user '{current_user.email}'",
    )
    await session.commit()
    service = AssessmentService(session)
    return await service.get_assessment_job(assessment_id, current_user)
