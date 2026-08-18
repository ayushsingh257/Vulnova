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
    port: int = 8080

    # Database & Cache Connection Strings (Supports Local & Supabase-Managed PostgreSQL)
    database_url: str = (
        "postgresql+asyncpg://vulnova_admin:vulnova_secure_password@localhost:5432/vulnova_db"
    )
    supabase_database_url: str = ""
    supabase_db_host: str = ""
    supabase_db_port: int = 5432
    supabase_db_name: str = "postgres"
    supabase_db_user: str = "postgres"
    supabase_db_password: str = ""

    # Database Connection Pool & SSL Settings
    db_pool_size: int = 20
    db_max_overflow: int = 10
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800
    db_pool_pre_ping: bool = True
    db_ssl_mode: str = "prefer"  # "require", "prefer", "disable"

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
    def effective_database_url(self) -> str:
        """Return the active PostgreSQL connection URL, prioritizing Supabase configurations and ensuring asyncpg driver."""
        url = self.supabase_database_url.strip()
        if (
            not url
            and self.supabase_db_host.strip()
            and self.supabase_db_password.strip()
        ):
            url = (
                f"postgresql+asyncpg://{self.supabase_db_user}:{self.supabase_db_password}"
                f"@{self.supabase_db_host}:{self.supabase_db_port}/{self.supabase_db_name}"
            )
        if not url:
            url = self.database_url.strip()

        # Normalize URL scheme for SQLAlchemy 2.0 async engine
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and not url.startswith(
            "postgresql+asyncpg://"
        ):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

        return url

    @property
    def is_supabase(self) -> bool:
        """Return True if the current database URL points to a Supabase-managed instance."""
        url = self.effective_database_url.lower()
        return "supabase.co" in url or "supabase.com" in url or "pooler.supabase" in url

    @property
    def is_development(self) -> bool:
        """Return True if environment is development."""
        return self.environment.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Return True if environment is production."""
        return self.environment.lower() in ("production", "prod")


settings = Settings()
