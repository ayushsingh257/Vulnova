"""FastAPI Router for Phase 6.5 Distributed Scan Scheduler & Recurrence Engine (/api/v1/scan-schedules)."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.rbac import require_permission
from app.application.assessment.dto import (
    CreateScanScheduleRequest,
    ScanScheduleListResponse,
    ScanScheduleResponse,
    UpdateScanScheduleRequest,
    WorkerAutoscaleMetricsResponse,
)
from app.application.assessment.scan_scheduler_service import ScanSchedulerService
from app.domain.entities.scan_schedule import (
    RecurrenceFrequency,
    ScanSchedule,
    ScheduleStatus,
)
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.scan_schedule_repository import (
    ScanScheduleRepository,
)
from app.infrastructure.database.repositories.scan_target_repository import (
    ScanTargetRepository,
)
from app.infrastructure.database.repositories.worker_repository import WorkerRepository
from app.infrastructure.database.session import get_async_session
from app.infrastructure.workers.worker_autoscaler import WorkerAutoscalerService

router = APIRouter(tags=["Scan Schedule Management"])


def _map_schedule_to_response(schedule: ScanSchedule) -> ScanScheduleResponse:
    """Map domain ScanSchedule to ScanScheduleResponse DTO."""
    return ScanScheduleResponse(
        id=str(schedule.id),
        organization_id=str(schedule.organization_id),
        scan_target_id=str(schedule.scan_target_id),
        name=schedule.name,
        cron_expression=schedule.cron_expression,
        frequency=schedule.frequency.value,
        status=schedule.status.value,
        profile_id=schedule.profile_id,
        enabled_plugins=schedule.enabled_plugins,
        total_runs_count=schedule.total_runs_count,
        next_run_at=schedule.next_run_at.isoformat() if schedule.next_run_at else "",
        last_run_at=schedule.last_run_at.isoformat() if schedule.last_run_at else None,
        created_by=str(schedule.created_by) if schedule.created_by else None,
        created_at=schedule.created_at.isoformat() if schedule.created_at else "",
        updated_at=schedule.updated_at.isoformat() if schedule.updated_at else "",
    )


def get_scheduler_service(
    session: AsyncSession = Depends(get_async_session),
) -> ScanSchedulerService:
    """Dependency factory creating ScanSchedulerService instance with session repos."""
    schedule_repo = ScanScheduleRepository(session)
    target_repo = ScanTargetRepository(session)
    return ScanSchedulerService(schedule_repo=schedule_repo, target_repo=target_repo)


@router.post(
    "",
    response_model=ScanScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("scans:schedule"))],
)
async def create_scan_schedule(
    req: CreateScanScheduleRequest,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    service: ScanSchedulerService = Depends(get_scheduler_service),
) -> ScanScheduleResponse:
    """Create a new recurring scan schedule for an authorized target asset.

    Requires authentication and 'scans:schedule' RBAC permission.
    Validates target registration, authorization contract, and max active tenant limits (max 20).
    """
    freq = (
        RecurrenceFrequency(req.frequency.upper())
        if req.frequency
        else RecurrenceFrequency.DAILY
    )
    schedule = await service.create_schedule(
        organization_id=current_user.organization_id,
        scan_target_id=UUID(req.scan_target_id),
        name=req.name,
        cron_expression=req.cron_expression,
        frequency=freq,
        profile_id=req.profile_id,
        enabled_plugins=req.enabled_plugins,
        created_by=current_user.id,
    )
    return _map_schedule_to_response(schedule)


@router.get(
    "",
    response_model=ScanScheduleListResponse,
    dependencies=[Depends(require_permission("scans:read"))],
)
async def list_scan_schedules(
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: UserModel = Depends(get_current_user_or_api_key),
    service: ScanSchedulerService = Depends(get_scheduler_service),
) -> ScanScheduleListResponse:
    """List recurring scan schedules for the authenticated organization.

    Requires 'scans:read' permission. Supports status filtering and pagination.
    """
    stat = ScheduleStatus(status_filter.upper()) if status_filter else None
    schedules, total = await service.list_schedules(
        organization_id=current_user.organization_id,
        status=stat,
        skip=skip,
        limit=limit,
    )
    return ScanScheduleListResponse(
        total_count=total, schedules=[_map_schedule_to_response(s) for s in schedules]
    )


@router.get(
    "/{schedule_id}",
    response_model=ScanScheduleResponse,
    dependencies=[Depends(require_permission("scans:read"))],
)
async def get_scan_schedule(
    schedule_id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    service: ScanSchedulerService = Depends(get_scheduler_service),
) -> ScanScheduleResponse:
    """Get details of a specific scan schedule by ID."""
    schedule = await service.get_schedule(schedule_id, current_user.organization_id)
    return _map_schedule_to_response(schedule)


@router.put(
    "/{schedule_id}",
    response_model=ScanScheduleResponse,
    dependencies=[Depends(require_permission("scans:schedule"))],
)
async def update_scan_schedule(
    schedule_id: UUID,
    req: UpdateScanScheduleRequest,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    service: ScanSchedulerService = Depends(get_scheduler_service),
) -> ScanScheduleResponse:
    """Update name, cron expression, profile, or plugins of an existing scan schedule."""
    freq = RecurrenceFrequency(req.frequency.upper()) if req.frequency else None
    schedule = await service.update_schedule(
        schedule_id=schedule_id,
        organization_id=current_user.organization_id,
        name=req.name,
        cron_expression=req.cron_expression,
        frequency=freq,
        profile_id=req.profile_id,
        enabled_plugins=req.enabled_plugins,
        updated_by=current_user.id,
    )
    return _map_schedule_to_response(schedule)


@router.post(
    "/{schedule_id}/pause",
    response_model=ScanScheduleResponse,
    dependencies=[Depends(require_permission("scans:schedule"))],
)
async def pause_scan_schedule(
    schedule_id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    service: ScanSchedulerService = Depends(get_scheduler_service),
) -> ScanScheduleResponse:
    """Pause an active scan schedule."""
    schedule = await service.pause_schedule(
        schedule_id, current_user.organization_id, current_user.id
    )
    return _map_schedule_to_response(schedule)


@router.post(
    "/{schedule_id}/resume",
    response_model=ScanScheduleResponse,
    dependencies=[Depends(require_permission("scans:schedule"))],
)
async def resume_scan_schedule(
    schedule_id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    service: ScanSchedulerService = Depends(get_scheduler_service),
) -> ScanScheduleResponse:
    """Resume a paused scan schedule."""
    schedule = await service.resume_schedule(
        schedule_id, current_user.organization_id, current_user.id
    )
    return _map_schedule_to_response(schedule)


@router.delete(
    "/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("scans:schedule"))],
)
async def delete_scan_schedule(
    schedule_id: UUID,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    service: ScanSchedulerService = Depends(get_scheduler_service),
) -> None:
    """Disable/soft-delete a scan schedule."""
    await service.delete_schedule(
        schedule_id, current_user.organization_id, current_user.id
    )


@router.post(
    "/tick",
    response_model=List[Dict[str, Any]],
    dependencies=[Depends(require_permission("scans:schedule"))],
)
async def trigger_scheduler_tick(
    current_user: UserModel = Depends(get_current_user_or_api_key),
    service: ScanSchedulerService = Depends(get_scheduler_service),
) -> List[Dict[str, Any]]:
    """Manually trigger a scheduler tick executing all due active scan schedules."""
    return await service.execute_due_schedules()


@router.get(
    "/workers/autoscale-metrics",
    response_model=WorkerAutoscaleMetricsResponse,
    dependencies=[Depends(require_permission("workers:read"))],
)
async def get_worker_autoscale_metrics(
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> WorkerAutoscaleMetricsResponse:
    """Get worker cluster capacity metrics and non-invasive autoscaling recommendations."""
    worker_repo = WorkerRepository(session)
    active_nodes = await worker_repo.list_worker_nodes(current_user.organization_id)
    autoscaler = WorkerAutoscalerService()
    metrics = autoscaler.calculate_cluster_metrics(active_nodes, pending_queue_depth=0)
    return WorkerAutoscaleMetricsResponse(
        active_workers_count=metrics.active_workers_count,
        idle_workers_count=metrics.idle_workers_count,
        pending_queue_depth=metrics.pending_queue_depth,
        recommended_workers_count=metrics.recommended_workers_count,
        scaling_action_suggested=metrics.scaling_action_suggested,
        timestamp=metrics.timestamp.isoformat(),
    )
