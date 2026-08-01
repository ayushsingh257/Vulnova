from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Vulnova Backend Application Settings."""

    app_name: str = "Vulnova Enterprise AppSec Control Plane"
    environment: str = "development"
    log_level: str = "INFO"
    host: str = "0.0.0.0"  # noqa: S104
    port: int = 8000

    database_url: str = (
        "postgresql+asyncpg://vulnova_admin:vulnova_secure_password@localhost:5432/vulnova_db"
    )
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "vulnova_dev_jwt_secret_key_32_characters_minimum"  # noqa: S105
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )


settings = Settings()
