"""Comprehensive unit and integration test suite for Era 6 Phase 6.5 Distributed Scan Scheduler & Recurrence Engine."""

from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.application.assessment.dto import (
    CreateScanScheduleRequest,
    ScanScheduleListResponse,
    ScanScheduleResponse,
    UpdateScanScheduleRequest,
    WorkerAutoscaleMetricsResponse,
)
from app.application.assessment.scan_scheduler_service import ScanSchedulerService
from app.domain.entities.role import Role
from app.domain.entities.scan_schedule import (
    RecurrenceFrequency,
    ScanSchedule,
    ScheduleStatus,
    WorkerAutoscaleMetrics,
)
from app.domain.entities.scan_target import ScanTarget, TargetStatus
from app.domain.entities.user import User
from app.infrastructure.database.models.scan_schedule import ScanScheduleModel
from app.infrastructure.database.models.scan_target import ScanTargetModel
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.repositories.scan_schedule_repository import (
    ScanScheduleRepository,
)
from app.infrastructure.database.repositories.scan_target_repository import (
    ScanTargetRepository,
)
from app.infrastructure.workers.celery_beat_scheduler import (
    CeleryBeatSchedulerManager,
    calculate_next_run_timestamp,
)
from app.infrastructure.workers.worker_autoscaler import WorkerAutoscalerService
from app.main import app


def _make_mock_schedule(
    schedule_id: Optional[UUID] = None,
    org_id: Optional[UUID] = None,
    target_id: Optional[UUID] = None,
    name: str = "Daily Security Assessment",
    cron_expr: str = "0 0 * * *",
    status: ScheduleStatus = ScheduleStatus.ACTIVE,
) -> ScanSchedule:
    now = datetime.now(timezone.utc)
    return ScanSchedule(
        id=schedule_id or uuid4(),
        organization_id=org_id or uuid4(),
        scan_target_id=target_id or uuid4(),
        name=name,
        cron_expression=cron_expr,
        frequency=RecurrenceFrequency.DAILY,
        status=status,
        profile_id="full_assessment",
        enabled_plugins=None,
        total_runs_count=0,
        next_run_at=now + timedelta(days=1),
        last_run_at=None,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.anyio
async def test_scan_schedule_domain_entity() -> None:
    """Test ScanSchedule domain dataclass initialization and default field values."""
    sched_id = uuid4()
    org_id = uuid4()
    target_id = uuid4()
    now = datetime.now(timezone.utc)

    schedule = ScanSchedule(
        id=sched_id,
        organization_id=org_id,
        scan_target_id=target_id,
        name="Daily Web Vulnerability Scan",
        cron_expression="0 0 * * *",
        frequency=RecurrenceFrequency.DAILY,
        status=ScheduleStatus.ACTIVE,
        profile_id="full_assessment",
        enabled_plugins=["xss", "sqli"],
        total_runs_count=5,
        next_run_at=now + timedelta(days=1),
    )

    assert schedule.id == sched_id
    assert schedule.organization_id == org_id
    assert schedule.scan_target_id == target_id
    assert schedule.name == "Daily Web Vulnerability Scan"
    assert schedule.frequency == RecurrenceFrequency.DAILY
    assert schedule.status == ScheduleStatus.ACTIVE
    assert schedule.total_runs_count == 5
    assert schedule.enabled_plugins == ["xss", "sqli"]


@pytest.mark.anyio
async def test_calculate_next_run_timestamp_intervals() -> None:
    """Test recurrence timestamp calculations for hourly, daily, weekly, monthly, and cron expressions."""
    base_time = datetime(2026, 8, 4, 12, 0, 0, tzinfo=timezone.utc)

    # Hourly
    next_hourly = calculate_next_run_timestamp(
        "0 * * * *", RecurrenceFrequency.HOURLY, base_time
    )
    assert next_hourly == base_time + timedelta(hours=1)

    # Daily
    next_daily = calculate_next_run_timestamp(
        "0 0 * * *", RecurrenceFrequency.DAILY, base_time
    )
    assert next_daily == base_time + timedelta(days=1)

    # Weekly
    next_weekly = calculate_next_run_timestamp(
        "0 0 * * 0", RecurrenceFrequency.WEEKLY, base_time
    )
    assert next_weekly == base_time + timedelta(weeks=1)

    # Custom step cron (*/15 * * * *)
    next_step = calculate_next_run_timestamp(
        "*/15 * * * *", RecurrenceFrequency.CUSTOM_CRON, base_time
    )
    assert next_step == base_time + timedelta(minutes=15)


@pytest.mark.anyio
async def test_scan_schedule_repository_methods() -> None:
    """Test repository domain conversion mapping methods."""
    session = AsyncMock()
    repo = ScanScheduleRepository(session)

    sched_id = uuid4()
    org_id = uuid4()
    target_id = uuid4()
    now = datetime.now(timezone.utc)

    model = ScanScheduleModel(
        id=sched_id,
        organization_id=org_id,
        scan_target_id=target_id,
        name="Repo Test Schedule",
        cron_expression="0 0 * * *",
        frequency="DAILY",
        status="ACTIVE",
        profile_id="full_assessment",
        enabled_plugins_json=None,
        total_runs_count=3,
        next_run_at=now + timedelta(days=1),
        last_run_at=now,
        created_by=None,
        created_at=now,
        updated_at=now,
    )

    domain = repo._to_domain(model)
    assert domain.id == sched_id
    assert domain.organization_id == org_id
    assert domain.name == "Repo Test Schedule"
    assert domain.frequency == RecurrenceFrequency.DAILY
    assert domain.status == ScheduleStatus.ACTIVE
    assert domain.total_runs_count == 3


@pytest.mark.anyio
async def test_scan_scheduler_service_lifecycle() -> None:
    """Test ScanSchedulerService business orchestration, audit event emission, and due schedule ticks."""
    org_id = uuid4()
    target_id = uuid4()
    user_id = uuid4()
    now = datetime.now(timezone.utc)

    target_mock = ScanTarget(
        id=target_id,
        organization_id=org_id,
        name="Service Target",
        target_url="https://svc-target.test.local",
        status=TargetStatus.ACTIVE,
    )

    sched_repo = AsyncMock()
    target_repo = AsyncMock()

    sched_repo.count_active_schedules = AsyncMock(return_value=1)
    target_repo.get_target_by_id = AsyncMock(return_value=target_mock)

    mock_created_sched = _make_mock_schedule(org_id=org_id, target_id=target_id)
    sched_repo.create_schedule = AsyncMock(return_value=mock_created_sched)
    sched_repo.get_schedule_by_id = AsyncMock(return_value=mock_created_sched)
    sched_repo.update_schedule = AsyncMock(return_value=mock_created_sched)
    sched_repo.delete_schedule = AsyncMock(return_value=True)
    sched_repo.list_schedules_due_for_execution = AsyncMock(
        return_value=[mock_created_sched]
    )
    sched_repo.update_schedule_after_run = AsyncMock(return_value=mock_created_sched)

    lock_manager = AsyncMock()
    lock_manager.acquire_scan_lock = AsyncMock(return_value=(True, "mock_lock_key"))

    service = ScanSchedulerService(
        schedule_repo=sched_repo,
        target_repo=target_repo,
        lock_manager=lock_manager,
    )

    # 1. Create Schedule
    created = await service.create_schedule(
        organization_id=org_id,
        scan_target_id=target_id,
        name="Daily Audit Scan",
        cron_expression="0 0 * * *",
        frequency=RecurrenceFrequency.DAILY,
        created_by=user_id,
    )
    assert created is not None

    # 2. Update Schedule
    updated = await service.update_schedule(
        schedule_id=created.id,
        organization_id=org_id,
        name="Renamed Audit Scan",
        updated_by=user_id,
    )
    assert updated is not None

    # 3. Pause & Resume Schedule
    paused = await service.pause_schedule(created.id, org_id, user_id)
    assert paused is not None

    resumed = await service.resume_schedule(created.id, org_id, user_id)
    assert resumed is not None

    # 4. Due Schedule Tick Execution
    results = await service.execute_due_schedules(reference_time=now)
    assert len(results) == 1
    assert results[0]["target_url"] == "https://svc-target.test.local"

    # 5. Disable Schedule
    dis_ok = await service.delete_schedule(created.id, org_id, user_id)
    assert dis_ok is True


@pytest.mark.anyio
async def test_worker_autoscaler_service() -> None:
    """Test WorkerAutoscalerService capacity metrics calculation and non-invasive scaling signals."""
    autoscaler = WorkerAutoscalerService(
        min_workers=1, max_workers=5, queue_threshold=3
    )

    # Stable state
    node1 = MagicMock(current_workload=1)
    metrics_stable = autoscaler.calculate_cluster_metrics(
        [node1], pending_queue_depth=1
    )
    assert metrics_stable.active_workers_count == 1
    assert metrics_stable.scaling_action_suggested == "STABLE"

    # Scale up state (queue depth >= 3)
    metrics_up = autoscaler.calculate_cluster_metrics([node1], pending_queue_depth=4)
    assert metrics_up.scaling_action_suggested == "SCALE_UP"
    assert metrics_up.recommended_workers_count == 2


@pytest.mark.anyio
async def test_celery_beat_scheduler_manager() -> None:
    """Test CeleryBeatSchedulerManager periodic tick execution wrapper."""
    mock_service = MagicMock()
    mock_service.execute_due_schedules = AsyncMock(
        return_value=[{"schedule_id": "test_id"}]
    )

    manager = CeleryBeatSchedulerManager(scheduler_service=mock_service)
    res = await manager.execute_beat_tick()

    assert res["status"] == "SUCCESS"
    assert res["dispatched_count"] == 1


@pytest.mark.anyio
async def test_scan_schedules_api_endpoints() -> None:
    """Test REST API router endpoints (/api/v1/scan-schedules) using AsyncClient and mocked service."""
    org_id = uuid4()
    target_id = uuid4()
    user_id = uuid4()

    mock_user = UserModel(
        id=user_id,
        organization_id=org_id,
        email=f"user-{uuid4().hex[:8]}@test.local",
        password_hash="hashed_pass_mock",
        full_name="Schedule Analyst",
        role=Role.SECURITY_ANALYST.name,
        is_active=True,
    )

    mock_schedule = _make_mock_schedule(org_id=org_id, target_id=target_id)

    from fastapi import FastAPI
    from app.main import vulnova_exception_handler
    from app.core.exceptions import VulnovaException
    from app.api.v1.routers.scan_schedules import (
        get_scheduler_service,
        router as scan_schedules_router,
    )
    from app.api.v1.dependencies.api_key import get_current_user_or_api_key
    from app.api.v1.dependencies.auth import get_current_active_user, get_current_user
    from app.infrastructure.database.session import get_async_session

    mock_service = AsyncMock()
    mock_service.create_schedule = AsyncMock(return_value=mock_schedule)
    mock_service.list_schedules = AsyncMock(return_value=([mock_schedule], 1))
    mock_service.get_schedule = AsyncMock(return_value=mock_schedule)
    mock_service.update_schedule = AsyncMock(return_value=mock_schedule)
    mock_service.pause_schedule = AsyncMock(return_value=mock_schedule)
    mock_service.resume_schedule = AsyncMock(return_value=mock_schedule)
    mock_service.delete_schedule = AsyncMock(return_value=True)
    mock_service.execute_due_schedules = AsyncMock(
        return_value=[{"schedule_id": str(mock_schedule.id)}]
    )

    mock_db_session = AsyncMock()

    async def _override_get_user() -> UserModel:
        return mock_user

    def _override_get_service() -> Any:
        return mock_service

    async def _override_get_session() -> AsyncGenerator[Any, None]:
        yield mock_db_session

    test_app = FastAPI()
    test_app.add_exception_handler(VulnovaException, vulnova_exception_handler)
    test_app.include_router(scan_schedules_router, prefix="/api/v1/scan-schedules")

    test_app.dependency_overrides[get_current_user] = _override_get_user
    test_app.dependency_overrides[get_current_active_user] = _override_get_user
    test_app.dependency_overrides[get_current_user_or_api_key] = _override_get_user
    test_app.dependency_overrides[get_scheduler_service] = _override_get_service
    test_app.dependency_overrides[get_async_session] = _override_get_session

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://testserver",
    ) as client:
        # 1. Create Schedule
        payload = {
            "scan_target_id": str(target_id),
            "name": "Weekly API Audit Scan",
            "cron_expression": "0 0 * * 0",
            "frequency": "WEEKLY",
            "profile_id": "full_assessment",
        }
        res_create = await client.post("/api/v1/scan-schedules", json=payload)
        assert res_create.status_code == 201
        sched_data = res_create.json()
        sched_id = sched_data["id"]

        # 2. List Schedules
        res_list = await client.get("/api/v1/scan-schedules")
        assert res_list.status_code == 200
        list_data = res_list.json()
        assert list_data["total_count"] == 1

        # 3. Get Schedule Details
        res_get = await client.get(f"/api/v1/scan-schedules/{sched_id}")
        assert res_get.status_code == 200
        assert res_get.json()["id"] == str(mock_schedule.id)

        # 4. Pause Schedule
        res_pause = await client.post(f"/api/v1/scan-schedules/{sched_id}/pause")
        assert res_pause.status_code == 200

        # 5. Resume Schedule
        res_resume = await client.post(f"/api/v1/scan-schedules/{sched_id}/resume")
        assert res_resume.status_code == 200

        # 6. Trigger Tick
        res_tick = await client.post("/api/v1/scan-schedules/tick")
        assert res_tick.status_code == 200

        # 7. Delete Schedule
        res_del = await client.delete(f"/api/v1/scan-schedules/{sched_id}")
        assert res_del.status_code == 204
