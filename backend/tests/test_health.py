from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint() -> None:
    """Verify root endpoint returns operational metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "Vulnova" in data["platform"]


def test_health_check_endpoint() -> None:
    """Verify /health endpoint returns HTTP 200 healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "vulnova-backend-control-plane"


def test_readiness_endpoint() -> None:
    """Verify /ready endpoint returns HTTP 200 status."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
