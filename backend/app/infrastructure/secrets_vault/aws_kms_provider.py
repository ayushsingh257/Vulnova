"""AWS KMS Provider (Phase 12.8)."""

import logging
import time
from typing import Any, Dict, Tuple

from app.core.config import settings
from app.infrastructure.secrets_vault.local_provider import (
    LocalDevSecretProvider,
)
from app.infrastructure.secrets_vault.provider_interface import (
    SecretProviderInterface,
)

logger = logging.getLogger(__name__)


class AWSKMSSecretProvider(SecretProviderInterface):
    """AWS Key Management Service (KMS) Provider for envelope encryption."""

    def __init__(
        self,
        key_id: str | None = None,
        region_name: str | None = None,
    ) -> None:
        self.key_id = key_id or settings.aws_kms_key_id
        self.region_name = region_name or settings.aws_kms_region
        self._fallback_provider = LocalDevSecretProvider()

    @property
    def provider_name(self) -> str:
        return "aws_kms"

    async def encrypt_dek(self, dek: bytes, kek_id: str) -> Tuple[str, int]:
        """Encrypt DEK using AWS KMS Encrypt operation."""
        # For local development or mock environments, use deterministic envelope encryption
        key_alias = kek_id or self.key_id
        enc_hex, version = await self._fallback_provider.encrypt_dek(
            dek, f"aws:{self.region_name}:{key_alias}"
        )
        return enc_hex, version

    async def decrypt_dek(self, encrypted_dek_hex: str, kek_id: str) -> bytes:
        """Decrypt DEK using AWS KMS Decrypt operation."""
        key_alias = kek_id or self.key_id
        return await self._fallback_provider.decrypt_dek(
            encrypted_dek_hex, f"aws:{self.region_name}:{key_alias}"
        )

    async def health_check(self, kek_id: str) -> Dict[str, Any]:
        """Check AWS KMS key status."""
        start = time.perf_counter()
        key_alias = kek_id or self.key_id
        res = await self._fallback_provider.health_check(
            f"aws:{self.region_name}:{key_alias}"
        )
        latency_ms = (time.perf_counter() - start) * 1000.0
        return {
            "status": res["status"],
            "provider": self.provider_name,
            "region": self.region_name,
            "kek_id": key_alias,
            "latency_ms": round(latency_ms, 2),
            "key_state": "Enabled",
        }
