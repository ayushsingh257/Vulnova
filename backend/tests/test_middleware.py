from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.core.exceptions import ResourceNotFoundException
from app.main import app

# Register dummy router for testing custom exception handler
dummy_router = APIRouter(prefix="/test-exceptions")


@dummy_router.get("/not-found")
async def trigger_not_found() -> None:
    raise ResourceNotFoundException("Target scan policy does not exist")


app.include_router(dummy_router)

client = TestClient(app)


def test_request_id_middleware_generated() -> None:
    """Verify X-Request-ID is generated automatically when absent."""
    response = client.get("/")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0


def test_request_id_middleware_preserved() -> None:
    """Verify X-Request-ID header value is preserved when client provides it."""
    custom_request_id = "req-test-12345-uuid"
    response = client.get("/", headers={"X-Request-ID": custom_request_id})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == custom_request_id


def test_security_headers_middleware() -> None:
    """Verify OWASP recommended security headers are present."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    assert "Strict-Transport-Security" in response.headers
    assert "Content-Security-Policy" in response.headers


def test_global_exception_handler_format() -> None:
    """Verify global exception handler formats error into standard enterprise schema."""
    response = client.get("/test-exceptions/not-found")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert data["error"]["message"] == "Target scan policy does not exist"
    assert "request_id" in data["error"]
