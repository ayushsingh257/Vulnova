"""Application Service orchestrating distributed Celery worker task dispatching, sandbox security compliance, and cluster monitoring."""

from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.assessment.dto import (
    DispatchScanRequest,
    SandboxConfigDTO,
    WorkerClusterMetricsDTO,
    WorkerNodeDTO,
    WorkerTaskExecutionDTO,
)
from app.application.audit_logs.services import AuditLogService
from app.core.exceptions import ResourceNotFoundException
from app.core.logging import get_logger
from app.infrastructure.database.models.worker import WorkerTaskModel
from app.infrastructure.database.repositories.worker_repository import WorkerRepository
from app.infrastructure.workers.sandbox_config import WorkerSandboxManager
from app.infrastructure.workers.tasks import (
    cancel_scan_job_task,
    execute_scan_job_task,
)

logger = get_logger(__name__)


class WorkerOrchestratorService:
    """Application Service orchestrating distributed worker job dispatching, sandbox safety, and cluster monitoring."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.worker_repo = WorkerRepository(session)
        self.audit_service = AuditLogService(session)
        self.sandbox_manager = WorkerSandboxManager()

    async def register_heartbeat(
        self,
        organization_id: UUID,
        worker_id: str,
        hostname: str = "localhost",
        status: str = "IDLE",
        current_task_count: int = 0,
        max_concurrency: int = 4,
        memory_usage_mb: float = 0.0,
        cpu_percent: float = 0.0,
    ) -> WorkerNodeDTO:
        """Register worker node or update heartbeat in cluster inventory."""
        node = await self.worker_repo.register_or_heartbeat_worker_node(
            organization_id=organization_id,
            worker_id=worker_id,
            hostname=hostname,
            status=status,
            current_task_count=current_task_count,
            max_concurrency=max_concurrency,
            memory_usage_mb=memory_usage_mb,
            cpu_percent=cpu_percent,
        )
        return self._map_node_to_dto(node)

    async def list_worker_nodes(
        self, organization_id: UUID, status: Optional[str] = None
    ) -> List[WorkerNodeDTO]:
        """List active worker nodes in cluster for organization."""
        nodes = await self.worker_repo.list_worker_nodes(
            organization_id=organization_id, status=status
        )
        return [self._map_node_to_dto(n) for n in nodes]

    async def get_cluster_metrics(
        self, organization_id: UUID
    ) -> WorkerClusterMetricsDTO:
        """Compute cluster metrics for organization worker pool."""
        raw_metrics = await self.worker_repo.get_cluster_metrics(organization_id)
        return WorkerClusterMetricsDTO(**raw_metrics)

    async def dispatch_scan_job(
        self, organization_id: UUID, requested_by: UUID, req: DispatchScanRequest
    ) -> WorkerTaskExecutionDTO:
        """Dispatch scan job to Celery priority queue with container sandbox security validation."""
        scan_id = UUID(req.scan_id)
        priority = req.priority or "scans.default"

        # 1. Validate sandbox environment security compliance
        task_id = f"task-{uuid4().hex[:12]}"
        sandbox_env = self.sandbox_manager.validate_task_sandbox_environment(
            organization_id=organization_id, task_id=task_id
        )

        # 2. Dispatch Task to Celery Priority Queue
        try:
            async_res = execute_scan_job_task.apply_async(
                args=[
                    str(scan_id),
                    str(organization_id),
                    str(requested_by),
                    req.profile_id,
                    req.target_url,
                ],
                task_id=task_id,
                queue=priority,
            )
            dispatched_task_id = async_res.id if hasattr(async_res, "id") else task_id
        except Exception as e:
            logger.warning("celery_dispatch_fallback", error=str(e))
            dispatched_task_id = task_id

        # 3. Log Task Execution Audit Entry
        task_model = WorkerTaskModel(
            task_id=dispatched_task_id,
            scan_id=scan_id,
            organization_id=organization_id,
            requested_by=requested_by,
            priority=priority,
            task_name="execute_scan_job_task",
            state="PENDING",
            retry_count=0,
            runtime_ms=0,
        )
        saved = await self.worker_repo.log_task_execution(task_model)

        await self.audit_service.record_event(
            organization_id=organization_id,
            action="worker_task.dispatched",
            resource_type="worker_task",
            resource_id=dispatched_task_id,
            actor_user_id=requested_by,
            details={
                "scan_id": req.scan_id,
                "priority": priority,
                "sandbox_env": sandbox_env,
            },
        )

        return self._map_task_to_dto(saved)

    async def cancel_task_execution(
        self, organization_id: UUID, requested_by: UUID, task_id: str
    ) -> WorkerTaskExecutionDTO:
        """Cancel a running task execution and signal sandbox termination."""
        existing = await self.worker_repo.get_task_execution(organization_id, task_id)
        if not existing:
            raise ResourceNotFoundException(f"Worker task '{task_id}' not found.")

        # Signal cancellation via Celery task
        try:
            cancel_scan_job_task.apply_async(
                args=[
                    str(existing.scan_id) if existing.scan_id else "",
                    str(organization_id),
                    str(requested_by),
                ],
                queue="scans.high",
            )
        except Exception as e:
            logger.warning("celery_cancel_signal_fallback", error=str(e))

        existing.state = "CANCELLED"
        existing.completed_at = datetime.now(timezone.utc)
        saved = await self.worker_repo.log_task_execution(existing)

        await self.audit_service.record_event(
            organization_id=organization_id,
            action="worker_task.cancelled",
            resource_type="worker_task",
            resource_id=task_id,
            actor_user_id=requested_by,
            details={"scan_id": str(existing.scan_id) if existing.scan_id else None},
        )

        return self._map_task_to_dto(saved)

    async def get_task_status(
        self, organization_id: UUID, task_id: str
    ) -> WorkerTaskExecutionDTO:
        """Retrieve task execution record by task_id with tenant boundary checks."""
        task_model = await self.worker_repo.get_task_execution(organization_id, task_id)
        if not task_model:
            raise ResourceNotFoundException(f"Worker task '{task_id}' not found.")
        return self._map_task_to_dto(task_model)

    def _map_node_to_dto(self, node: Any) -> WorkerNodeDTO:
        """Map worker node ORM model to DTO."""
        return WorkerNodeDTO(
            id=str(node.id),
            organization_id=str(node.organization_id),
            worker_id=node.worker_id,
            hostname=node.hostname,
            status=node.status,
            current_task_count=node.current_task_count,
            max_concurrency=node.max_concurrency,
            memory_usage_mb=node.memory_usage_mb,
            cpu_percent=node.cpu_percent,
            queue_subscriptions=node.queue_subscriptions or [],
            sandbox_limits=SandboxConfigDTO(**(node.sandbox_limits or {})),
            last_heartbeat=(
                node.last_heartbeat.isoformat() if node.last_heartbeat else ""
            ),
        )

    def _map_task_to_dto(self, task: Any) -> WorkerTaskExecutionDTO:
        """Map worker task execution ORM model to DTO."""
        return WorkerTaskExecutionDTO(
            id=str(task.id),
            task_id=task.task_id,
            scan_id=str(task.scan_id) if task.scan_id else None,
            organization_id=str(task.organization_id),
            requested_by=str(task.requested_by),
            worker_node_id=str(task.worker_node_id) if task.worker_node_id else None,
            priority=task.priority,
            task_name=task.task_name,
            state=task.state,
            retry_count=task.retry_count,
            runtime_ms=task.runtime_ms,
            error_message=task.error_message,
            created_at=task.created_at.isoformat() if task.created_at else "",
            started_at=task.started_at.isoformat() if task.started_at else None,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
        )
