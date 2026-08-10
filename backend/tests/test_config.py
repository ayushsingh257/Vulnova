from app.core.config import settings


def test_settings_initialization() -> None:
    """Verify application configuration settings properties."""
    assert settings.app_name is not None
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.port == 8080
    assert settings.database_url is not None
    assert settings.redis_url is not None


def test_environment_helpers() -> None:
    """Verify environment evaluation helper properties."""
    assert isinstance(settings.is_development, bool)
    assert isinstance(settings.is_production, bool)
