"""Repository for worker node heartbeats, capacity lookup, task state auditing, and metrics calculation."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.worker import (
    WorkerNodeModel,
    WorkerTaskModel,
)


class WorkerRepository:
    """Repository managing worker cluster node registrations, heartbeats, task execution auditing, and tenant metrics."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def register_or_heartbeat_worker_node(
        self,
        organization_id: UUID,
        worker_id: str,
        hostname: str = "localhost",
        status: str = "IDLE",
        current_task_count: int = 0,
        max_concurrency: int = 4,
        memory_usage_mb: float = 0.0,
        cpu_percent: float = 0.0,
        queue_subscriptions: Optional[List[str]] = None,
        sandbox_limits: Optional[Dict[str, Any]] = None,
    ) -> WorkerNodeModel:
        """Register a new worker node or update heartbeat for an existing node."""
        stmt = select(WorkerNodeModel).where(
            WorkerNodeModel.organization_id == organization_id,
            WorkerNodeModel.worker_id == worker_id,
        )
        result = await self.session.execute(stmt)
        node = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)

        if not node:
            node = WorkerNodeModel(
                organization_id=organization_id,
                worker_id=worker_id,
                hostname=hostname,
                status=status,
                current_task_count=current_task_count,
                max_concurrency=max_concurrency,
                memory_usage_mb=memory_usage_mb,
                cpu_percent=cpu_percent,
                queue_subscriptions=queue_subscriptions or ["scans.default"],
                sandbox_limits=sandbox_limits
                or {
                    "cpu_limit_vcpu": 1.0,
                    "memory_limit_mb": 512,
                    "read_only_rootfs": True,
                    "no_new_privs": True,
                    "run_as_uid": 10001,
                },
                last_heartbeat=now,
            )
            self.session.add(node)
        else:
            node.status = status
            node.current_task_count = current_task_count
            node.memory_usage_mb = memory_usage_mb
            node.cpu_percent = cpu_percent
            node.last_heartbeat = now
            if queue_subscriptions:
                node.queue_subscriptions = queue_subscriptions
            if sandbox_limits:
                node.sandbox_limits = sandbox_limits

        await self.session.flush()
        return node

    async def get_worker_node(
        self, organization_id: UUID, worker_id: str
    ) -> Optional[WorkerNodeModel]:
        """Fetch worker node by worker_id and tenant organization_id."""
        stmt = select(WorkerNodeModel).where(
            WorkerNodeModel.organization_id == organization_id,
            WorkerNodeModel.worker_id == worker_id,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_worker_nodes(
        self, organization_id: UUID, status: Optional[str] = None
    ) -> List[WorkerNodeModel]:
        """List worker nodes belonging to tenant organization."""
        stmt = select(WorkerNodeModel).where(
            WorkerNodeModel.organization_id == organization_id
        )
        if status:
            stmt = stmt.where(WorkerNodeModel.status == status)
        stmt = stmt.order_by(WorkerNodeModel.last_heartbeat.desc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def log_task_execution(
        self, task_execution: WorkerTaskModel
    ) -> WorkerTaskModel:
        """Create or update task execution audit record."""
        stmt = select(WorkerTaskModel).where(
            WorkerTaskModel.organization_id == task_execution.organization_id,
            WorkerTaskModel.task_id == task_execution.task_id,
        )
        res = await self.session.execute(stmt)
        existing = res.scalar_one_or_none()

        if not existing:
            self.session.add(task_execution)
            await self.session.flush()
            return task_execution

        existing.state = task_execution.state
        existing.runtime_ms = task_execution.runtime_ms
        existing.error_message = task_execution.error_message
        existing.completed_at = task_execution.completed_at
        await self.session.flush()
        return existing

    async def get_task_execution(
        self, organization_id: UUID, task_id: str
    ) -> Optional[WorkerTaskModel]:
        """Fetch task execution record by task_id with tenant boundary checks."""
        stmt = select(WorkerTaskModel).where(
            WorkerTaskModel.organization_id == organization_id,
            WorkerTaskModel.task_id == task_id,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_cluster_metrics(self, organization_id: UUID) -> Dict[str, Any]:
        """Compute cluster metrics for organization worker pool."""
        nodes = await self.list_worker_nodes(organization_id)

        total_nodes = len(nodes)
        active_nodes = sum(1 for n in nodes if n.status in ("IDLE", "BUSY"))
        total_capacity = sum(n.max_concurrency for n in nodes)
        current_active_tasks = sum(n.current_task_count for n in nodes)

        avg_cpu = (
            sum(n.cpu_percent for n in nodes) / total_nodes if total_nodes > 0 else 0.0
        )
        avg_memory = (
            sum(n.memory_usage_mb for n in nodes) / total_nodes
            if total_nodes > 0
            else 0.0
        )

        return {
            "organization_id": str(organization_id),
            "total_nodes": total_nodes,
            "active_nodes": active_nodes,
            "total_capacity": total_capacity,
            "current_active_tasks": current_active_tasks,
            "avg_cpu_percent": round(avg_cpu, 2),
            "avg_memory_usage_mb": round(avg_memory, 2),
        }
