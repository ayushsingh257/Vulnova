from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.infrastructure.database.base import Base
from app.main import app

client = TestClient(app)


def test_base_declarative_class() -> None:
    """Verify DeclarativeBase model metadata exists."""
    assert Base.metadata is not None


@patch(
    "app.main.check_database_connection",
    new_callable=AsyncMock,
    return_value=True,
)
def test_readiness_probe_database_connected(mock_check_db: AsyncMock) -> None:
    """Verify /ready endpoint returns status ready when database connection succeeds."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"] == "connected"
    mock_check_db.assert_called_once()


@patch(
    "app.main.check_database_connection",
    new_callable=AsyncMock,
    return_value=False,
)
def test_readiness_probe_database_disconnected(
    mock_check_db: AsyncMock,
) -> None:
    """Verify /ready endpoint returns degraded status when database is disconnected."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["database"] == "disconnected"
    mock_check_db.assert_called_once()
