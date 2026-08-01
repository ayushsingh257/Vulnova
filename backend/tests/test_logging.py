"""Phase 1.7 — Structured Logging & Correlation ID Test Suite."""

import json
import logging
from io import StringIO

import structlog
from fastapi.testclient import TestClient

from app.core.correlation import get_correlation_id, set_correlation_id
from app.core.logging import get_logger, setup_logging
from app.main import app
import tests.test_middleware  # noqa: F401

client = TestClient(app)


# ───────────────────────────────────────────────
# Component 1: structlog configuration tests
# ───────────────────────────────────────────────


def test_get_logger_returns_bound_logger() -> None:
    """Verify get_logger() returns a structlog BoundLogger instance."""
    log = get_logger("test.module")
    assert log is not None
    # structlog bound loggers have bind/unbind methods
    assert hasattr(log, "bind")
    assert hasattr(log, "unbind")
    assert hasattr(log, "info")
    assert hasattr(log, "warning")
    assert hasattr(log, "error")


def test_setup_logging_configures_root_logger() -> None:
    """Verify setup_logging() configures the root logger with a handler."""
    setup_logging()
    root = logging.getLogger()
    assert len(root.handlers) > 0
    handler = root.handlers[0]
    assert hasattr(handler, "formatter")
    assert handler.formatter is not None


# ───────────────────────────────────────────────
# Component 2: correlation ID context tests
# ───────────────────────────────────────────────


def test_correlation_id_default() -> None:
    """Verify default correlation ID is 'unknown'."""
    from app.core.correlation import correlation_id_ctx

    token = correlation_id_ctx.set("unknown")
    assert get_correlation_id() == "unknown"
    correlation_id_ctx.reset(token)


def test_set_and_get_correlation_id() -> None:
    """Verify set_correlation_id and get_correlation_id round-trip correctly."""
    set_correlation_id("test-corr-id-12345")
    assert get_correlation_id() == "test-corr-id-12345"
    # Reset to avoid leaking state
    set_correlation_id("unknown")


# ───────────────────────────────────────────────
# Component 3: RequestIDMiddleware structlog binding
# ───────────────────────────────────────────────


def test_request_id_middleware_binds_to_response() -> None:
    """Verify X-Request-ID appears in response headers."""
    response = client.get("/")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0


def test_request_id_middleware_preserves_client_id() -> None:
    """Verify client-provided X-Request-ID is preserved."""
    custom_id = "client-req-id-abc-789"
    response = client.get("/", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_id


# ───────────────────────────────────────────────
# Component 5: Request Logging Middleware
# ───────────────────────────────────────────────


def test_request_logging_produces_output() -> None:
    """Verify that HTTP request logging middleware runs without error."""
    # This test verifies the middleware executes successfully on a request
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_request_logging_on_api_v1() -> None:
    """Verify request logging works on API v1 routes."""
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    assert "status" in response.json()


# ───────────────────────────────────────────────
# Component 4: Exception handler structured logging
# ───────────────────────────────────────────────


def test_exception_handler_returns_request_id() -> None:
    """Verify exception handler response includes request_id field."""
    response = client.get("/test-exceptions/not-found")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert "request_id" in data["error"]


def test_structured_log_output_contains_json() -> None:
    """Verify that structlog produces valid structured output."""
    # Capture log output by writing to a string buffer
    buffer = StringIO()
    handler = logging.StreamHandler(buffer)

    # Use the same formatter structlog would use
    from structlog.stdlib import ProcessorFormatter

    formatter = ProcessorFormatter(
        processors=[
            ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )
    handler.setFormatter(formatter)

    test_logger = logging.getLogger("test.structured_output")
    test_logger.addHandler(handler)
    test_logger.setLevel(logging.INFO)

    # Emit a log via structlog
    sl = structlog.get_logger("test.structured_output")
    sl.info("test_event", key="value", number=42)

    output = buffer.getvalue().strip()
    assert len(output) > 0

    # Parse the JSON output
    log_entry = json.loads(output)
    assert log_entry["event"] == "test_event"
    assert log_entry["key"] == "value"
    assert log_entry["number"] == 42

    # Cleanup
    test_logger.removeHandler(handler)
