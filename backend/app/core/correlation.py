"""Vulnova Correlation ID Context Variable Module.

Provides async-safe correlation ID propagation using Python contextvars.
The correlation ID is automatically bound to structlog context by the
RequestIDMiddleware, making it appear in every log line within a request.
"""

from contextvars import ContextVar

correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="unknown")


def get_correlation_id() -> str:
    """Return the current correlation ID from async context.

    Returns:
        The active correlation ID string, or 'unknown' if not set.
    """
    return correlation_id_ctx.get()


def set_correlation_id(value: str) -> None:
    """Set the correlation ID in the current async context.

    Args:
        value: The correlation ID string to bind.
    """
    correlation_id_ctx.set(value)
