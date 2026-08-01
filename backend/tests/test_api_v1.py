from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@patch(
    "app.api.v1.routers.status.check_database_connection",
    new_callable=AsyncMock,
    return_value=True,
)
def test_api_v1_status_endpoint_connected(mock_check_db: AsyncMock) -> None:
    """Verify /api/v1/status endpoint when database is connected."""
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert data["api_version"] == "v1"
    assert data["status"] == "operational"
    assert data["services"]["database"] == "connected"
    mock_check_db.assert_called_once()


@patch(
    "app.api.v1.routers.status.check_database_connection",
    new_callable=AsyncMock,
    return_value=False,
)
def test_api_v1_status_endpoint_disconnected(mock_check_db: AsyncMock) -> None:
    """Verify /api/v1/status endpoint when database is disconnected."""
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert data["api_version"] == "v1"
    assert data["status"] == "degraded"
    assert data["services"]["database"] == "disconnected"
    mock_check_db.assert_called_once()
