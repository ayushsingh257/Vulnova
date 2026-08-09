"""KMS Provider Registry and Factory (Phase 12.8)."""

from typing import Dict, List

from app.core.config import settings
from app.infrastructure.secrets_vault.aws_kms_provider import (
    AWSKMSSecretProvider,
)
from app.infrastructure.secrets_vault.gcp_kms_provider import (
    GCPKMSSecretProvider,
)
from app.infrastructure.secrets_vault.local_provider import (
    LocalDevSecretProvider,
)
from app.infrastructure.secrets_vault.provider_interface import (
    SecretProviderInterface,
)
from app.infrastructure.secrets_vault.vault_provider import (
    VaultSecretProvider,
)


class KMSProviderRegistry:
    """Registry maintaining active Key Management System provider drivers."""

    def __init__(self) -> None:
        self._providers: Dict[str, SecretProviderInterface] = {
            "local": LocalDevSecretProvider(),
            "vault": VaultSecretProvider(),
            "aws_kms": AWSKMSSecretProvider(),
            "gcp_kms": GCPKMSSecretProvider(),
        }

    def register_provider(self, provider: SecretProviderInterface) -> None:
        """Register or override a KMS provider driver."""
        self._providers[provider.provider_name] = provider

    def get_provider(self, provider_name: str | None = None) -> SecretProviderInterface:
        """Retrieve configured or requested KMS provider driver.

        Args:
            provider_name: Optional provider identifier. Defaults to settings.kms_provider.

        Returns:
            Instantiated SecretProviderInterface implementation.
        """
        name = (provider_name or settings.kms_provider).lower().strip()
        if name in self._providers:
            return self._providers[name]
        # Fallback to local provider if unknown
        return self._providers["local"]

    def list_supported_providers(self) -> List[str]:
        """List all supported KMS provider identifiers."""
        return list(self._providers.keys())


# Singleton registry instance
kms_registry = KMSProviderRegistry()
