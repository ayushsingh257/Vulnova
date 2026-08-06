"""Unit and Integration Test Suite for Centralized Observability, Telemetry & Health Monitoring."""

import pytest
from starlette.testclient import TestClient

from app.infrastructure.observability.logging_service import (
    mask_sensitive_data,
    structured_logger,
)
from app.infrastructure.observability.metrics.metrics_service import metrics_service
from app.infrastructure.observability.tracing_service import tracing_service
from app.main import app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_sensitive_data_masking() -> None:
    """Verify sensitive key values like password, jwt, and secret are redacted in log payloads."""
    payload = {
        "event": "user.login",
        "username": "alice",
        "password": "SuperSecretPassword123!",
        "jwt_secret": "my-secret-key-32-chars",
        "authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        "nested": {"api_key": "vn_live_abcdef123456"},
    }

    sanitized = mask_sensitive_data(payload)
    assert sanitized["username"] == "alice"
    assert sanitized["password"] == "******** [REDACTED]"
    assert sanitized["jwt_secret"] == "******** [REDACTED]"
    assert "REDACTED" in sanitized["authorization"]
    assert sanitized["nested"]["api_key"] == "******** [REDACTED]"


def test_structured_logger_execution() -> None:
    """Verify StructuredLoggingService formats log entries with request and environment context."""
    log_dict = structured_logger.log_event(
        level="info",
        event_name="test_audit_event",
        request_id="req-1234",
        user_id="usr-5678",
        extra={"action": "vulnerability.triage"},
    )
    assert log_dict["event"] == "test_audit_event"
    assert log_dict["request_id"] == "req-1234"
    assert log_dict["user_id"] == "usr-5678"
    assert log_dict["severity"] == "INFO"


def test_prometheus_metrics_generation() -> None:
    """Verify Prometheus text format output rendering."""
    metrics_service.record_http_request(
        method="GET", endpoint="/api/v1/status", status_code=200, duration_ms=15.2
    )
    metrics_service.record_db_query(duration_ms=45.0, is_slow=True)
    metrics_service.record_cache_access(hit=True)
    metrics_service.record_security_event(event_type="auth_failure")

    prometheus_text = metrics_service.generate_prometheus_text()
    assert "vulnova_http_requests_total" in prometheus_text
    assert "vulnova_db_slow_queries_total" in prometheus_text
    assert "vulnova_redis_cache_requests_total" in prometheus_text
    assert "vulnova_auth_failures_total" in prometheus_text


def test_tracing_service_spans() -> None:
    """Verify OpenTelemetry tracer span creation context managers."""
    with tracing_service.trace_db_query(
        statement_type="SELECT", table_name="users"
    ) as span:
        assert span is not None

    with tracing_service.trace_redis_op(command="GET", key="tenant:org1") as span:
        assert span is not None


def test_system_health_endpoints() -> None:
    """Verify /metrics, /api/v1/system/health, /readiness, and /liveness endpoints."""
    client = TestClient(app)

    # 1. Prometheus Metrics Endpoint
    metrics_res = client.get("/metrics")
    assert metrics_res.status_code == 200
    assert "text/plain" in metrics_res.headers["content-type"]
    assert "vulnova_http_requests_total" in metrics_res.text

    # 2. System Health Summary Endpoint
    health_res = client.get("/api/v1/system/health")
    assert health_res.status_code == 200
    data = health_res.json()
    assert "status" in data
    assert "dependencies" in data
    assert "uptime_seconds" in data

    # 3. System Readiness Probe
    readiness_res = client.get("/api/v1/system/readiness")
    assert readiness_res.status_code in [200, 503]

    # 4. System Liveness Probe
    liveness_res = client.get("/api/v1/system/liveness")
    assert liveness_res.status_code == 200
    assert liveness_res.json()["status"] == "ALIVE"


def test_request_tracing_middleware_headers() -> None:
    """Verify X-Request-ID and X-Correlation-ID headers are present in response."""
    client = TestClient(app)
    custom_request_id = "test-req-id-100"
    custom_correlation_id = "test-corr-id-200"

    headers = {
        "X-Request-ID": custom_request_id,
        "X-Correlation-ID": custom_correlation_id,
    }
    res = client.get("/api/v1/system/liveness", headers=headers)

    assert res.status_code == 200
    assert res.headers["X-Request-ID"] == custom_request_id
    assert res.headers["X-Correlation-ID"] == custom_correlation_id
