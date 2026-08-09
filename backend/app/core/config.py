from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Vulnova Enterprise AppSec Control Plane Configuration Settings."""

    app_name: str = "Vulnova Enterprise AppSec Control Plane"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"
    log_level: str = "INFO"
    host: str = "0.0.0.0"  # noqa: S104
    port: int = 8000

    # Database & Cache Connection Strings
    database_url: str = (
        "postgresql+asyncpg://vulnova_admin:vulnova_secure_password@localhost:5432/vulnova_db"
    )
    redis_url: str = "redis://localhost:6379/0"

    # Security & JWT Token Configurations
    jwt_secret: str = "vulnova_dev_jwt_secret_key_32_characters_minimum"  # noqa: S105
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])

    # AI Provider Key Placeholders
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # External KMS & Enterprise Secrets Vault Configurations (Phase 12.8)
    kms_provider: str = "local"  # "local", "vault", "aws_kms", "gcp_kms"
    vault_addr: str = "http://localhost:8200"
    vault_token: str = ""
    vault_transit_key: str = "vulnova-kek"
    aws_kms_key_id: str = "alias/vulnova-kek"
    aws_kms_region: str = "us-east-1"
    gcp_kms_key_name: str = (
        "projects/vulnova-prod/locations/global/keyRings/vulnova-ring/cryptoKeys/vulnova-kek"
    )
    secret_default_rotation_days: int = 90

    # Antivirus & Evidence Upload Protection Configurations (Phase 12.9)
    clamav_host: str = "localhost"
    clamav_port: int = 3310
    clamav_timeout: int = 10
    minio_quarantine_bucket: str = "vulnova-quarantine-bucket"
    minio_production_bucket: str = "vulnova-evidence-bucket"
    yara_rules_dir: str = "security/yara_rules"

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @property
    def is_development(self) -> bool:
        """Return True if environment is development."""
        return self.environment.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Return True if environment is production."""
        return self.environment.lower() in ("production", "prod")


settings = Settings()
