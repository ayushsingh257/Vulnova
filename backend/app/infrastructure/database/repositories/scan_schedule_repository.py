"""Repository for Phase 6.5 Distributed Scan Schedule CRUD and due schedule queries."""

from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domain.entities.scan_schedule import (
    RecurrenceFrequency,
    ScanSchedule,
    ScheduleStatus,
)
from app.infrastructure.database.models.scan_schedule import ScanScheduleModel

logger = get_logger("vulnova.scan_schedule_repository")


class ScanScheduleRepository:
    """Repository managing persistence and database-backed queries for recurring scan schedules."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, model: ScanScheduleModel) -> ScanSchedule:
        """Convert ORM model to domain entity."""
        return ScanSchedule(
            id=model.id,
            organization_id=model.organization_id,
            scan_target_id=model.scan_target_id,
            name=model.name,
            cron_expression=model.cron_expression,
            frequency=RecurrenceFrequency(model.frequency),
            status=ScheduleStatus(model.status),
            profile_id=model.profile_id,
            enabled_plugins=(
                model.enabled_plugins_json
                if isinstance(model.enabled_plugins_json, list)
                else None
            ),
            total_runs_count=model.total_runs_count,
            next_run_at=model.next_run_at,
            last_run_at=model.last_run_at,
            created_by=model.created_by,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def create_schedule(self, schedule: ScanSchedule) -> ScanSchedule:
        """Persist a new scan schedule in the database."""
        model = ScanScheduleModel(
            id=schedule.id,
            organization_id=schedule.organization_id,
            scan_target_id=schedule.scan_target_id,
            name=schedule.name,
            cron_expression=schedule.cron_expression,
            frequency=schedule.frequency.value,
            status=schedule.status.value,
            profile_id=schedule.profile_id,
            enabled_plugins_json=schedule.enabled_plugins,
            total_runs_count=schedule.total_runs_count,
            next_run_at=schedule.next_run_at,
            last_run_at=schedule.last_run_at,
            created_by=schedule.created_by,
            created_at=schedule.created_at,
            updated_at=schedule.updated_at,
        )
        self.session.add(model)
        await self.session.flush()
        logger.info(
            "scan_schedule.repository_created",
            schedule_id=str(model.id),
            org_id=str(model.organization_id),
            next_run_at=model.next_run_at.isoformat(),
        )
        return self._to_domain(model)

    async def get_schedule_by_id(
        self, schedule_id: UUID, organization_id: UUID
    ) -> Optional[ScanSchedule]:
        """Fetch scan schedule by ID enforcing organization multi-tenant boundary."""
        stmt = select(ScanScheduleModel).where(
            ScanScheduleModel.id == schedule_id,
            ScanScheduleModel.organization_id == organization_id,
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def list_schedules(
        self,
        organization_id: UUID,
        status: Optional[ScheduleStatus] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ScanSchedule], int]:
        """List scan schedules for an organization with pagination and optional status filter."""
        base_stmt = select(ScanScheduleModel).where(
            ScanScheduleModel.organization_id == organization_id
        )
        if status:
            base_stmt = base_stmt.where(ScanScheduleModel.status == status.value)

        # Count total
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total_count = (await self.session.execute(count_stmt)).scalar() or 0

        # Page query
        page_stmt = (
            base_stmt.order_by(ScanScheduleModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(page_stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models], total_count

    async def count_active_schedules(self, organization_id: UUID) -> int:
        """Count active scan schedules for an organization."""
        stmt = select(func.count(ScanScheduleModel.id)).where(
            ScanScheduleModel.organization_id == organization_id,
            ScanScheduleModel.status == ScheduleStatus.ACTIVE.value,
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def update_schedule(self, schedule: ScanSchedule) -> ScanSchedule:
        """Update existing scan schedule."""
        stmt = select(ScanScheduleModel).where(
            ScanScheduleModel.id == schedule.id,
            ScanScheduleModel.organization_id == schedule.organization_id,
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            raise ValueError(f"ScanSchedule {schedule.id} not found")

        model.name = schedule.name
        model.cron_expression = schedule.cron_expression
        model.frequency = schedule.frequency.value
        model.status = schedule.status.value
        model.profile_id = schedule.profile_id
        model.enabled_plugins_json = schedule.enabled_plugins
        model.next_run_at = schedule.next_run_at
        model.last_run_at = schedule.last_run_at
        model.total_runs_count = schedule.total_runs_count
        model.updated_at = datetime.now(timezone.utc)

        await self.session.flush()
        return self._to_domain(model)

    async def delete_schedule(self, schedule_id: UUID, organization_id: UUID) -> bool:
        """Soft-delete / disable scan schedule."""
        stmt = select(ScanScheduleModel).where(
            ScanScheduleModel.id == schedule_id,
            ScanScheduleModel.organization_id == organization_id,
        )
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return False

        model.status = ScheduleStatus.DISABLED.value
        model.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True

    async def list_schedules_due_for_execution(
        self, reference_time: Optional[datetime] = None, limit: int = 50
    ) -> List[ScanSchedule]:
        """Fetch all active scan schedules where next_run_at <= reference_time."""
        now = reference_time or datetime.now(timezone.utc)
        stmt = (
            select(ScanScheduleModel)
            .where(
                ScanScheduleModel.status == ScheduleStatus.ACTIVE.value,
                ScanScheduleModel.next_run_at <= now,
            )
            .order_by(ScanScheduleModel.next_run_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def update_schedule_after_run(
        self, schedule_id: UUID, next_run_at: datetime, last_run_at: datetime
    ) -> Optional[ScanSchedule]:
        """Atomically update next_run_at, last_run_at, and increment total_runs_count after an execution tick."""
        stmt = select(ScanScheduleModel).where(ScanScheduleModel.id == schedule_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None

        model.next_run_at = next_run_at
        model.last_run_at = last_run_at
        model.total_runs_count += 1
        model.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return self._to_domain(model)
