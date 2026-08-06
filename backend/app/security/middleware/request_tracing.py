"""Request Tracing Middleware generating request_id, correlation_id, and capturing execution telemetry."""

import time
from typing import Any, Callable
from uuid import uuid4

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.infrastructure.observability.logging_service import structured_logger
from app.infrastructure.observability.metrics.metrics_service import metrics_service
from app.infrastructure.observability.tracing_service import tracing_service

logger = structlog.get_logger(__name__)


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Middleware enriching requests with correlation context and recording execution telemetry."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Response:
        """Trace request lifecycle, inject headers, and record metrics."""
        start_time = time.perf_counter()

        # 1. Capture or Generate Request ID and Correlation ID
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        correlation_id = request.headers.get("X-Correlation-ID") or request_id

        request.state.request_id = request_id
        request.state.correlation_id = correlation_id

        # 2. Process Request inside OpenTelemetry Span
        with tracing_service.start_span(
            name=f"HTTP {request.method} {request.url.path}",
            attributes={
                "http.method": request.method,
                "http.target": request.url.path,
                "request_id": request_id,
                "correlation_id": correlation_id,
            },
        ):
            response: Response = await call_next(request)

        # 3. Calculate Execution Duration
        duration_ms = (time.perf_counter() - start_time) * 1000.0

        # 4. Inject Tracing Headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id

        # 5. Record Metrics & Telemetry Log
        metrics_service.record_http_request(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        structured_logger.log_event(
            level="info" if response.status_code < 400 else "warning",
            event_name="http_request_completed",
            request_id=request_id,
            correlation_id=correlation_id,
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )

        return response
