"""Celery Beat Scheduler Manager handling periodic cron ticks and recurring scan dispatches."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from app.core.logging import get_logger
from app.domain.entities.scan_schedule import (
    RecurrenceFrequency,
)

logger = get_logger("vulnova.celery_beat_scheduler")


def calculate_next_run_timestamp(
    cron_expression: str,
    frequency: RecurrenceFrequency = RecurrenceFrequency.DAILY,
    base_time: Optional[datetime] = None,
) -> datetime:
    """Calculate the next UTC datetime execution timestamp for a given schedule.

    Supports croniter library if present, or deterministic recurrence fallback calculations.
    """
    now = base_time or datetime.now(timezone.utc)

    # Try croniter if installed
    try:
        import croniter

        iter_obj = croniter.croniter(cron_expression, now)
        next_dt: datetime = iter_obj.get_next(datetime)
        if next_dt.tzinfo is None:
            next_dt = next_dt.replace(tzinfo=timezone.utc)
        return next_dt
    except Exception as exc:
        logger.debug("croniter_eval_fallback", error=str(exc))

    # Built-in recurrence calculation fallbacks
    expr = cron_expression.strip()
    if frequency == RecurrenceFrequency.HOURLY or expr in ("0 * * * *", "@hourly"):
        return now + timedelta(hours=1)
    elif frequency == RecurrenceFrequency.DAILY or expr in ("0 0 * * *", "@daily"):
        return now + timedelta(days=1)
    elif frequency == RecurrenceFrequency.WEEKLY or expr in ("0 0 * * 0", "@weekly"):
        return now + timedelta(weeks=1)
    elif frequency == RecurrenceFrequency.MONTHLY or expr in ("0 0 1 * *", "@monthly"):
        return now + timedelta(days=30)
    elif expr.startswith("*/"):
        try:
            mins = int(expr.split()[0].replace("*/", ""))
            return now + timedelta(minutes=max(1, mins))
        except (ValueError, IndexError):
            pass

    # Default fallback: 24 hours ahead
    return now + timedelta(days=1)


class CeleryBeatSchedulerManager:
    """Manager invoked periodically by Celery Beat to execute due scan schedules."""

    def __init__(self, scheduler_service: Any = None) -> None:
        self.scheduler_service = scheduler_service

    async def execute_beat_tick(self) -> Dict[str, Any]:
        """Execute periodic tick checking and dispatching all due scan schedules."""
        if not self.scheduler_service:
            logger.warning(
                "celery_beat.tick_skipped", reason="scheduler_service not bound"
            )
            return {"dispatched_count": 0, "status": "SKIPPED"}

        try:
            results = await self.scheduler_service.execute_due_schedules()
            logger.info("celery_beat.tick_executed", count=len(results))
            return {"dispatched_count": len(results), "status": "SUCCESS"}
        except Exception as e:
            logger.error("celery_beat.tick_failed", error=str(e))
            return {"dispatched_count": 0, "status": "ERROR", "error": str(e)}
