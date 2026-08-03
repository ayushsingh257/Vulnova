"""Unit & Integration Tests for Phase 6.1 Celery & Distributed Isolated Worker Sandbox Cluster."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.application.assessment.dto import DispatchScanRequest
from app.application.assessment.worker_orchestrator import WorkerOrchestratorService
from app.domain.entities.worker import (
    SandboxResourceLimits,
    WorkerNode,
    WorkerStatus,
    WorkerTaskExecution,
    WorkerTaskPriority,
    WorkerTaskState,
)
from app.infrastructure.database.models.worker import WorkerNodeModel, WorkerTaskModel
from app.infrastructure.workers.celery_app import celery_app
from app.infrastructure.workers.sandbox_config import WorkerSandboxManager
from app.infrastructure.workers.tasks import (
    cancel_scan_job_task,
    cleanup_scan_artifacts_task,
    execute_scan_job_task,
)


def test_celery_app_configuration() -> None:
    """Verify Celery app initialization and priority task routing settings."""
    assert celery_app.main == "vulnova_workers"
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"
    assert celery_app.conf.accept_content == ["json"]
    assert celery_app.conf.timezone == "UTC"
    assert celery_app.conf.task_ack_late is True
    assert "scans.default" in celery_app.conf.task_queues


def test_sandbox_manager_security_constraints() -> None:
    """Verify container sandbox security caps and unprivileged execution settings."""
    limits = SandboxResourceLimits()
    sandbox = WorkerSandboxManager(limits)

    sec_opts = sandbox.get_container_security_opt()
    assert "no-new-privileges:true" in sec_opts

    host_config = sandbox.get_container_host_config()
    assert host_config["Memory"] == 512 * 1024 * 1024
    assert host_config["NanoCpus"] == 1000000000
    assert host_config["PidsLimit"] == 100
    assert host_config["ReadonlyRootfs"] is True
    assert host_config["CapDrop"] == ["ALL"]
    assert host_config["User"] == "10001:10001"


def test_celery_tasks_sandbox_execution() -> None:
    """Verify Celery task execution flow returns sandbox compliance metadata without raw OS execution."""
    org_id = str(uuid4())
    user_id = str(uuid4())
    scan_id = str(uuid4())

    res = execute_scan_job_task.run(
        scan_id=scan_id,
        organization_id=org_id,
        requested_by=user_id,
        profile_id="full_dast",
        target_url="http://target.test",
    )

    assert res["status"] == "SUCCESS"
    assert res["scan_id"] == scan_id
    assert res["organization_id"] == org_id
    assert res["sandbox_environment"]["read_only_rootfs"] is True
    assert res["sandbox_environment"]["run_as_uid"] == 10001

    cancel_res = cancel_scan_job_task.run(
        scan_id=scan_id, organization_id=org_id, requested_by=user_id
    )
    assert cancel_res["status"] == "CANCELLED"

    cleanup_res = cleanup_scan_artifacts_task.run(
        scan_id=scan_id, organization_id=org_id
    )
    assert cleanup_res["status"] == "CLEANED"


@pytest.mark.anyio
async def test_worker_repository_heartbeat_and_node_management() -> None:
    """Test WorkerRepository node heartbeat registration, updates, and capacity lookup."""
    mock_session = MagicMock()
    service = WorkerOrchestratorService(mock_session)

    org_id = uuid4()
    worker_id = "worker-node-101"

    mock_node = WorkerNodeModel(
        id=uuid4(),
        organization_id=org_id,
        worker_id=worker_id,
        hostname="worker-host-1",
        status="IDLE",
        current_task_count=0,
        max_concurrency=4,
        memory_usage_mb=128.5,
        cpu_percent=12.4,
        queue_subscriptions=["scans.default"],
        sandbox_limits={"cpu_limit_vcpu": 1.0, "memory_limit_mb": 512},
        last_heartbeat=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    service.worker_repo.register_or_heartbeat_worker_node = AsyncMock(
        return_value=mock_node
    )

    dto = await service.register_heartbeat(
        organization_id=org_id,
        worker_id=worker_id,
        hostname="worker-host-1",
        status="IDLE",
        current_task_count=0,
        max_concurrency=4,
        memory_usage_mb=128.5,
        cpu_percent=12.4,
    )

    assert dto.worker_id == worker_id
    assert dto.hostname == "worker-host-1"
    assert dto.status == "IDLE"
    assert dto.max_concurrency == 4
    assert dto.sandbox_limits.memory_limit_mb == 512


@pytest.mark.anyio
async def test_worker_orchestrator_dispatch_and_cancel() -> None:
    """Test WorkerOrchestratorService scan job dispatching and cancellation."""
    mock_session = MagicMock()
    service = WorkerOrchestratorService(mock_session)

    org_id = uuid4()
    user_id = uuid4()
    scan_id = uuid4()

    req = DispatchScanRequest(
        scan_id=str(scan_id),
        profile_id="full_dast",
        target_url="http://example.com",
        priority="scans.high",
    )

    mock_saved_task = WorkerTaskModel(
        id=uuid4(),
        task_id="task-dispatched-101",
        scan_id=scan_id,
        organization_id=org_id,
        requested_by=user_id,
        priority="scans.high",
        task_name="execute_scan_job_task",
        state="PENDING",
        retry_count=0,
        runtime_ms=0,
        created_at=datetime.now(timezone.utc),
    )

    service.worker_repo.log_task_execution = AsyncMock(return_value=mock_saved_task)
    service.audit_service.record_event = AsyncMock()

    dto = await service.dispatch_scan_job(org_id, user_id, req)

    assert dto.scan_id == str(scan_id)
    assert dto.priority == "scans.high"
    assert dto.state == "PENDING"
    assert service.audit_service.record_event.called


@pytest.mark.anyio
async def test_worker_orchestrator_cluster_metrics() -> None:
    """Test WorkerOrchestratorService cluster metrics computation."""
    mock_session = MagicMock()
    service = WorkerOrchestratorService(mock_session)

    org_id = uuid4()

    mock_metrics = {
        "organization_id": str(org_id),
        "total_nodes": 3,
        "active_nodes": 3,
        "total_capacity": 12,
        "current_active_tasks": 2,
        "avg_cpu_percent": 18.5,
        "avg_memory_usage_mb": 256.0,
    }

    service.worker_repo.get_cluster_metrics = AsyncMock(return_value=mock_metrics)

    metrics = await service.get_cluster_metrics(org_id)

    assert metrics.total_nodes == 3
    assert metrics.total_capacity == 12
    assert metrics.current_active_tasks == 2
    assert metrics.avg_cpu_percent == 18.5


@pytest.mark.anyio
async def test_worker_tenant_boundary_isolation() -> None:
    """Test tenant boundary isolation for task execution status lookup."""
    mock_session = MagicMock()
    service = SecurityCopilotService = WorkerOrchestratorService(mock_session)

    org_a = uuid4()
    task_id = "task-tenant-b-101"

    service.worker_repo.get_task_execution = AsyncMock(return_value=None)

    with pytest.raises(Exception):
        await service.get_task_status(org_a, task_id)
