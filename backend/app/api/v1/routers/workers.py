"""FastAPI Router for Distributed Worker Sandbox Cluster (/api/v1/workers/*)."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.rbac import require_permission
from app.application.assessment.dto import (
    DispatchScanRequest,
    WorkerClusterMetricsDTO,
    WorkerNodeDTO,
    WorkerTaskExecutionDTO,
)
from app.application.assessment.worker_orchestrator import WorkerOrchestratorService
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.session import get_async_session

router = APIRouter()


@router.post(
    "/heartbeat",
    response_model=WorkerNodeDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("workers:manage"))],
)
async def worker_heartbeat(
    worker_id: str = Query(..., description="Unique ID of worker node"),
    hostname: str = Query("localhost", description="Worker node hostname"),
    node_status: str = Query(
        "IDLE", alias="status", description="Worker status (IDLE, BUSY, OFFLINE)"
    ),
    current_task_count: int = Query(0, ge=0),
    max_concurrency: int = Query(4, ge=1),
    memory_usage_mb: float = Query(0.0, ge=0.0),
    cpu_percent: float = Query(0.0, ge=0.0),
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> WorkerNodeDTO:
    """Register a new worker node or update heartbeat in cluster inventory.

    Requires authentication and 'workers:manage' RBAC permission (ADMIN).
    """
    service = WorkerOrchestratorService(session)
    return await service.register_heartbeat(
        organization_id=current_user.organization_id,
        worker_id=worker_id,
        hostname=hostname,
        status=node_status,
        current_task_count=current_task_count,
        max_concurrency=max_concurrency,
        memory_usage_mb=memory_usage_mb,
        cpu_percent=cpu_percent,
    )


@router.get(
    "/nodes",
    response_model=List[WorkerNodeDTO],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("workers:read"))],
)
async def list_worker_nodes(
    status_filter: Optional[str] = Query(
        None, alias="status", description="Filter by node status"
    ),
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> List[WorkerNodeDTO]:
    """List worker nodes in cluster for organization.

    Requires authentication and 'workers:read' RBAC permission (VIEWER+).
    """
    service = WorkerOrchestratorService(session)
    return await service.list_worker_nodes(
        organization_id=current_user.organization_id, status=status_filter
    )


@router.get(
    "/metrics",
    response_model=WorkerClusterMetricsDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("workers:read"))],
)
async def get_worker_cluster_metrics(
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> WorkerClusterMetricsDTO:
    """Compute overall worker cluster metrics and active capacity.

    Requires authentication and 'workers:read' RBAC permission (VIEWER+).
    """
    service = WorkerOrchestratorService(session)
    return await service.get_cluster_metrics(
        organization_id=current_user.organization_id
    )


@router.post(
    "/jobs/dispatch",
    response_model=WorkerTaskExecutionDTO,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_permission("scans:dispatch"))],
)
async def dispatch_scan_job(
    req: DispatchScanRequest,
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> WorkerTaskExecutionDTO:
    """Dispatch scan job to Celery priority queues with container sandbox security validation.

    Requires authentication and 'scans:dispatch' RBAC permission (SECURITY_ANALYST+).
    """
    service = WorkerOrchestratorService(session)
    return await service.dispatch_scan_job(
        organization_id=current_user.organization_id,
        requested_by=current_user.id,
        req=req,
    )


@router.post(
    "/tasks/{task_id}/cancel",
    response_model=WorkerTaskExecutionDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("scans:dispatch"))],
)
async def cancel_worker_task(
    task_id: str = Path(..., description="Task ID to cancel"),
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> WorkerTaskExecutionDTO:
    """Cancel running worker task execution and signal sandbox termination.

    Requires authentication and 'scans:dispatch' RBAC permission (SECURITY_ANALYST+).
    """
    service = WorkerOrchestratorService(session)
    return await service.cancel_task_execution(
        organization_id=current_user.organization_id,
        requested_by=current_user.id,
        task_id=task_id,
    )


@router.get(
    "/tasks/{task_id}",
    response_model=WorkerTaskExecutionDTO,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_permission("workers:read"))],
)
async def get_worker_task_status(
    task_id: str = Path(..., description="Task ID to query"),
    current_user: UserModel = Depends(get_current_user_or_api_key),
    session: AsyncSession = Depends(get_async_session),
) -> WorkerTaskExecutionDTO:
    """Retrieve task execution record by task_id with tenant boundary checks.

    Requires authentication and 'workers:read' RBAC permission (VIEWER+).
    """
    service = WorkerOrchestratorService(session)
    return await service.get_task_status(
        organization_id=current_user.organization_id, task_id=task_id
    )
