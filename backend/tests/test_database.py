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


def test_supabase_database_url_normalization() -> None:
    """Verify Settings effective_database_url correctly normalizes Supabase URL schemes."""
    from app.core.config import Settings

    # Test standard postgres:// scheme converted to asyncpg
    s1 = Settings(
        database_url="postgres://postgres:secret@db.xyz.supabase.co:5432/postgres"
    )
    assert s1.effective_database_url.startswith("postgresql+asyncpg://")
    assert s1.is_supabase is True

    # Test Supabase direct pooler URL
    s2 = Settings(
        supabase_database_url="postgresql://postgres.proj:secret@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
    )
    assert s2.effective_database_url.startswith("postgresql+asyncpg://")
    assert s2.is_supabase is True

    # Test discrete Supabase variables
    s3 = Settings(
        supabase_db_host="db.myref.supabase.co",
        supabase_db_password="mypassword123",
        supabase_db_user="postgres",
        supabase_db_name="postgres",
    )
    assert s3.effective_database_url == (
        "postgresql+asyncpg://postgres:mypassword123@db.myref.supabase.co:5432/postgres"
    )
    assert s3.is_supabase is True


def test_supabase_engine_kwargs_resolution() -> None:
    """Verify _build_engine_kwargs configures statement caching for Supabase transaction pooler."""
    from app.core.config import Settings
    from app.infrastructure.database import session

    # With transaction pooler (port 6543)
    mock_settings = Settings(
        database_url="postgresql+asyncpg://postgres.ref:pw@aws-0.pooler.supabase.com:6543/postgres",
        db_ssl_mode="require",
    )
    with patch.object(session, "settings", mock_settings):
        kwargs = session._build_engine_kwargs()
        assert kwargs["connect_args"]["statement_cache_size"] == 0
        assert kwargs["connect_args"]["ssl"] == "require"
        assert kwargs["pool_pre_ping"] is True
