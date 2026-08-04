"""Application Service managing scan schedule creation, cron ticks, audit events, and lifecycle updates."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from app.core.exceptions import (
    ResourceNotFoundException,
    ValidationException,
)
from app.core.logging import get_logger
from app.domain.entities.scan_schedule import (
    RecurrenceFrequency,
    ScanSchedule,
    ScheduleStatus,
)
from app.infrastructure.database.repositories.scan_schedule_repository import (
    ScanScheduleRepository,
)
from app.infrastructure.database.repositories.scan_target_repository import (
    ScanTargetRepository,
)
from app.infrastructure.workers.celery_beat_scheduler import (
    calculate_next_run_timestamp,
)
from app.infrastructure.workers.scan_lock_manager import DistributedScanLockManager

logger = get_logger("vulnova.scan_scheduler_service")

MAX_ACTIVE_SCHEDULES_PER_ORG = 20


class ScanSchedulerService:
    """Application service governing recurring assessment schedules, authorization gates, and audit trails."""

    def __init__(
        self,
        schedule_repo: ScanScheduleRepository,
        target_repo: ScanTargetRepository,
        lock_manager: Optional[DistributedScanLockManager] = None,
        assessment_service: Optional[Any] = None,
        worker_orchestrator: Optional[Any] = None,
        audit_log_repo: Optional[Any] = None,
    ) -> None:
        self.schedule_repo = schedule_repo
        self.target_repo = target_repo
        self.lock_manager = lock_manager or DistributedScanLockManager()
        self.assessment_service = assessment_service
        self.worker_orchestrator = worker_orchestrator
        self.audit_log_repo = audit_log_repo

    async def _record_audit_event(
        self,
        action: str,
        organization_id: UUID,
        user_id: Optional[UUID],
        details: Dict[str, Any],
    ) -> None:
        """Helper recording structured audit trail events."""
        logger.info(
            action,
            organization_id=str(organization_id),
            user_id=str(user_id) if user_id else "SYSTEM",
            **details,
        )

    async def create_schedule(
        self,
        organization_id: UUID,
        scan_target_id: UUID,
        name: str,
        cron_expression: str,
        frequency: RecurrenceFrequency = RecurrenceFrequency.DAILY,
        profile_id: str = "full_assessment",
        enabled_plugins: Optional[List[str]] = None,
        created_by: Optional[UUID] = None,
    ) -> ScanSchedule:
        """Create a new recurring scan schedule with authorization contract validation and limit safeguards."""
        # 1. Verify target exists and belongs to tenant org
        target = await self.target_repo.get_target_by_id(
            target_id=scan_target_id, organization_id=organization_id
        )
        if not target:
            raise ResourceNotFoundException(f"Scan target {scan_target_id} not found")

        if target.status != "ACTIVE":
            raise ValidationException(
                f"Scan target is not ACTIVE (current: {target.status})"
            )

        # 2. Check organization active schedule limit (Max 20 per tenant)
        active_count = await self.schedule_repo.count_active_schedules(organization_id)
        if active_count >= MAX_ACTIVE_SCHEDULES_PER_ORG:
            raise ValidationException(
                f"Organization active schedule limit ({MAX_ACTIVE_SCHEDULES_PER_ORG}) reached"
            )

        # 3. Calculate initial next_run_at timestamp
        next_run = calculate_next_run_timestamp(
            cron_expression=cron_expression, frequency=frequency
        )

        schedule = ScanSchedule(
            id=uuid4(),
            organization_id=organization_id,
            scan_target_id=scan_target_id,
            name=name.strip(),
            cron_expression=cron_expression.strip(),
            frequency=frequency,
            status=ScheduleStatus.ACTIVE,
            profile_id=profile_id,
            enabled_plugins=enabled_plugins,
            total_runs_count=0,
            next_run_at=next_run,
            last_run_at=None,
            created_by=created_by,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        created = await self.schedule_repo.create_schedule(schedule)

        # Record audit event: scan_schedule.created
        await self._record_audit_event(
            action="scan_schedule.created",
            organization_id=organization_id,
            user_id=created_by,
            details={
                "schedule_id": str(created.id),
                "scan_target_id": str(scan_target_id),
                "cron_expression": cron_expression,
                "frequency": frequency.value,
                "next_run_at": next_run.isoformat(),
            },
        )

        return created

    async def get_schedule(
        self, schedule_id: UUID, organization_id: UUID
    ) -> ScanSchedule:
        """Fetch schedule by ID with tenant boundary check."""
        schedule = await self.schedule_repo.get_schedule_by_id(
            schedule_id, organization_id
        )
        if not schedule:
            raise ResourceNotFoundException(f"Scan schedule {schedule_id} not found")
        return schedule

    async def list_schedules(
        self,
        organization_id: UUID,
        status: Optional[ScheduleStatus] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ScanSchedule], int]:
        """List scan schedules for tenant organization."""
        return await self.schedule_repo.list_schedules(
            organization_id=organization_id, status=status, skip=skip, limit=limit
        )

    async def update_schedule(
        self,
        schedule_id: UUID,
        organization_id: UUID,
        name: Optional[str] = None,
        cron_expression: Optional[str] = None,
        frequency: Optional[RecurrenceFrequency] = None,
        profile_id: Optional[str] = None,
        enabled_plugins: Optional[List[str]] = None,
        updated_by: Optional[UUID] = None,
    ) -> ScanSchedule:
        """Update an existing scan schedule and recompute next_run_at if cron modified."""
        schedule = await self.get_schedule(schedule_id, organization_id)

        if name is not None:
            schedule.name = name.strip()
        if profile_id is not None:
            schedule.profile_id = profile_id
        if enabled_plugins is not None:
            schedule.enabled_plugins = enabled_plugins

        if cron_expression is not None or frequency is not None:
            if cron_expression is not None:
                schedule.cron_expression = cron_expression.strip()
            if frequency is not None:
                schedule.frequency = frequency
            schedule.next_run_at = calculate_next_run_timestamp(
                cron_expression=schedule.cron_expression, frequency=schedule.frequency
            )

        updated = await self.schedule_repo.update_schedule(schedule)

        # Record audit event: scan_schedule.updated
        await self._record_audit_event(
            action="scan_schedule.updated",
            organization_id=organization_id,
            user_id=updated_by,
            details={
                "schedule_id": str(schedule_id),
                "name": updated.name,
                "cron_expression": updated.cron_expression,
                "next_run_at": updated.next_run_at.isoformat(),
            },
        )

        return updated

    async def pause_schedule(
        self, schedule_id: UUID, organization_id: UUID, user_id: Optional[UUID] = None
    ) -> ScanSchedule:
        """Pause active scan schedule."""
        schedule = await self.get_schedule(schedule_id, organization_id)
        if schedule.status == ScheduleStatus.PAUSED:
            return schedule

        schedule.status = ScheduleStatus.PAUSED
        updated = await self.schedule_repo.update_schedule(schedule)

        # Record audit event: scan_schedule.paused
        await self._record_audit_event(
            action="scan_schedule.paused",
            organization_id=organization_id,
            user_id=user_id,
            details={"schedule_id": str(schedule_id)},
        )

        return updated

    async def resume_schedule(
        self, schedule_id: UUID, organization_id: UUID, user_id: Optional[UUID] = None
    ) -> ScanSchedule:
        """Resume paused scan schedule and calculate next run time."""
        schedule = await self.get_schedule(schedule_id, organization_id)

        # Check tenant limit before resuming
        active_count = await self.schedule_repo.count_active_schedules(organization_id)
        if active_count >= MAX_ACTIVE_SCHEDULES_PER_ORG:
            raise ValidationException(
                f"Cannot resume schedule. Active limit ({MAX_ACTIVE_SCHEDULES_PER_ORG}) reached"
            )

        schedule.status = ScheduleStatus.ACTIVE
        schedule.next_run_at = calculate_next_run_timestamp(
            cron_expression=schedule.cron_expression, frequency=schedule.frequency
        )
        updated = await self.schedule_repo.update_schedule(schedule)

        # Record audit event: scan_schedule.resumed
        await self._record_audit_event(
            action="scan_schedule.resumed",
            organization_id=organization_id,
            user_id=user_id,
            details={
                "schedule_id": str(schedule_id),
                "next_run_at": updated.next_run_at.isoformat(),
            },
        )

        return updated

    async def delete_schedule(
        self, schedule_id: UUID, organization_id: UUID, user_id: Optional[UUID] = None
    ) -> bool:
        """Disable/delete scan schedule."""
        await self.get_schedule(schedule_id, organization_id)
        success = await self.schedule_repo.delete_schedule(schedule_id, organization_id)

        if success:
            # Record audit event: scan_schedule.disabled
            await self._record_audit_event(
                action="scan_schedule.disabled",
                organization_id=organization_id,
                user_id=user_id,
                details={"schedule_id": str(schedule_id)},
            )

        return success

    async def execute_due_schedules(
        self, reference_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Periodic tick worker: Fetches due active schedules, verifies targets, acquires target lock, and dispatches scans."""
        now = reference_time or datetime.now(timezone.utc)
        due_schedules = await self.schedule_repo.list_schedules_due_for_execution(now)

        dispatched_results: List[Dict[str, Any]] = []

        for schedule in due_schedules:
            # 1. Verify target exists and is still ACTIVE
            target = await self.target_repo.get_target_by_id(
                target_id=schedule.scan_target_id,
                organization_id=schedule.organization_id,
            )
            if not target or target.status != "ACTIVE":
                # Target is suspended or deleted -> disable schedule
                schedule.status = ScheduleStatus.DISABLED
                await self.schedule_repo.update_schedule(schedule)
                await self._record_audit_event(
                    action="scan_schedule.disabled",
                    organization_id=schedule.organization_id,
                    user_id=None,
                    details={
                        "schedule_id": str(schedule.id),
                        "reason": f"Scan target {schedule.scan_target_id} inactive or missing",
                    },
                )
                continue

            # 2. Acquire target concurrency lock (Phase 6.3 lock integration)
            lock_acquired = await self.lock_manager.acquire_lock(
                organization_id=schedule.organization_id,
                target_url=target.target_url,
                owner_id=str(schedule.id),
            )

            if not lock_acquired:
                logger.info(
                    "scan_schedule.skipped_lock_held",
                    schedule_id=str(schedule.id),
                    target_url=target.target_url,
                )
                continue

            # 3. Calculate next run timestamp & update schedule timestamps
            next_run = calculate_next_run_timestamp(
                cron_expression=schedule.cron_expression,
                frequency=schedule.frequency,
                base_time=now,
            )
            await self.schedule_repo.update_schedule_after_run(
                schedule_id=schedule.id, next_run_at=next_run, last_run_at=now
            )

            # 4. Trigger assessment scan execution
            job_id = uuid4()
            if self.assessment_service:
                try:
                    await self.assessment_service.create_and_run_assessment(
                        organization_id=schedule.organization_id,
                        target_url=target.target_url,
                        profile_id=schedule.profile_id,
                        enabled_plugins=schedule.enabled_plugins,
                        is_authorized_assessment=True,
                    )
                except Exception as e:
                    logger.error(
                        "scan_schedule.dispatch_error",
                        schedule_id=str(schedule.id),
                        error=str(e),
                    )

            # 5. Record audit event: scan_schedule.triggered
            await self._record_audit_event(
                action="scan_schedule.triggered",
                organization_id=schedule.organization_id,
                user_id=schedule.created_by,
                details={
                    "schedule_id": str(schedule.id),
                    "job_id": str(job_id),
                    "target_url": target.target_url,
                    "next_run_at": next_run.isoformat(),
                },
            )

            dispatched_results.append(
                {
                    "schedule_id": str(schedule.id),
                    "target_url": target.target_url,
                    "next_run_at": next_run.isoformat(),
                }
            )

        return dispatched_results
