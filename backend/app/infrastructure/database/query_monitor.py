"""Database Query Performance Monitoring Middleware & Event Listener."""

import time
from typing import Any, List

import structlog
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.infrastructure.database.performance.dto import SlowQueryLogDTO
from app.infrastructure.database.performance.query_analyzer import QueryAnalyzerService

logger = structlog.get_logger(__name__)

# Default threshold for slow query warnings (100 ms)
SLOW_QUERY_THRESHOLD_MS = 100.0


class DatabaseQueryMonitor:
    """Monitors SQLAlchemy cursor execution, calculates query duration, and flags slow queries (>100ms)."""

    def __init__(self, slow_threshold_ms: float = SLOW_QUERY_THRESHOLD_MS) -> None:
        self.slow_threshold_ms = slow_threshold_ms
        self.query_analyzer = QueryAnalyzerService()

    def attach_engine_listeners(self, sync_engine: Engine) -> None:
        """Attach before_cursor_execute and after_cursor_execute SQLAlchemy event listeners."""

        @event.listens_for(sync_engine, "before_cursor_execute")
        def before_cursor_execute(
            conn: Any,
            cursor: Any,
            statement: str,
            parameters: Any,
            context: Any,
            executemany: bool,
        ) -> None:
            context._query_start_time = time.perf_counter()

        @event.listens_for(sync_engine, "after_cursor_execute")
        def after_cursor_execute(
            conn: Any,
            cursor: Any,
            statement: str,
            parameters: Any,
            context: Any,
            executemany: bool,
        ) -> None:
            total_time_ms = (
                time.perf_counter()
                - getattr(context, "_query_start_time", time.perf_counter())
            ) * 1000.0
            if total_time_ms >= self.slow_threshold_ms:
                self.query_analyzer.log_slow_query(
                    statement=statement, duration_ms=total_time_ms
                )

    def get_slow_queries(self) -> List[SlowQueryLogDTO]:
        """Return list of recorded slow query logs."""
        return self.query_analyzer.slow_query_logs


# Global singleton monitor instance
query_monitor = DatabaseQueryMonitor()
