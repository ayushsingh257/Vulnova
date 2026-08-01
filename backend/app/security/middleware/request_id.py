"""Vulnova Request ID Traceability Middleware.

Attaches a unique X-Request-ID to every HTTP request and binds it into
the structlog context so all log lines within the request lifecycle
automatically include the correlation ID.
"""

import uuid
from typing import Awaitable, Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.correlation import set_correlation_id


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware attaching unique X-Request-ID trace identifier to each request."""

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        # Bind correlation ID into structlog context and contextvars
        set_correlation_id(request_id)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        # Clean up context after request completes
        structlog.contextvars.unbind_contextvars("request_id")
        return response
