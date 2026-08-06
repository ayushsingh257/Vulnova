"""OpenTelemetry Distributed Tracing Infrastructure with Jaeger / OTLP Compatibility."""

from contextlib import contextmanager
from typing import Any, Generator, Optional

import structlog

logger = structlog.get_logger(__name__)

try:
    from opentelemetry import trace

    HAS_OPENTELEMETRY = True
except ImportError:
    HAS_OPENTELEMETRY = False


class DummySpan:
    """Mock span when OpenTelemetry package is not installed."""

    def set_attribute(self, key: str, value: str) -> None:
        pass


class TracingService:
    """Service wrapping OpenTelemetry tracer provider for request, database, and Redis span management."""

    def __init__(self, service_name: str = "vulnova-backend") -> None:
        self.service_name = service_name
        if HAS_OPENTELEMETRY:
            self.tracer: Optional[Any] = trace.get_tracer(service_name)
        else:
            self.tracer = None

    @contextmanager
    def start_span(
        self,
        name: str,
        attributes: Optional[dict[str, Any]] = None,
    ) -> Generator[Any, None, None]:
        """Context manager creating an OpenTelemetry span."""
        if HAS_OPENTELEMETRY and self.tracer is not None:
            with self.tracer.start_as_current_span(name) as span:
                if attributes:
                    for k, v in attributes.items():
                        span.set_attribute(k, str(v))
                yield span
        else:
            dummy = DummySpan()
            if attributes:
                for k, v in attributes.items():
                    dummy.set_attribute(k, str(v))
            yield dummy

    @contextmanager
    def trace_db_query(
        self, statement_type: str, table_name: str
    ) -> Generator[Any, None, None]:
        """Trace a database query execution span."""
        span_name = f"DB {statement_type.upper()} {table_name}"
        attrs = {
            "db.system": "postgresql",
            "db.name": "vulnova_db",
            "db.sql.table": table_name,
        }
        with self.start_span(span_name, attributes=attrs) as span:
            yield span

    @contextmanager
    def trace_redis_op(self, command: str, key: str) -> Generator[Any, None, None]:
        """Trace a Redis command execution span."""
        span_name = f"Redis {command.upper()} {key}"
        attrs = {"db.system": "redis", "db.redis.key": key, "db.operation": command}
        with self.start_span(span_name, attributes=attrs) as span:
            yield span


# Global singleton instance
tracing_service = TracingService()
