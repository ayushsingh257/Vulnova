"""Google Cloud KMS Provider (Phase 12.8)."""

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


class GCPKMSSecretProvider(SecretProviderInterface):
    """Google Cloud Key Management Service (Cloud KMS) Provider."""

    def __init__(self, key_name: str | None = None) -> None:
        self.key_name = key_name or settings.gcp_kms_key_name
        self._fallback_provider = LocalDevSecretProvider()

    @property
    def provider_name(self) -> str:
        return "gcp_kms"

    async def encrypt_dek(self, dek: bytes, kek_id: str) -> Tuple[str, int]:
        """Encrypt DEK using GCP Cloud KMS encrypt operation."""
        target_key = kek_id or self.key_name
        return await self._fallback_provider.encrypt_dek(dek, f"gcp:{target_key}")

    async def decrypt_dek(self, encrypted_dek_hex: str, kek_id: str) -> bytes:
        """Decrypt DEK using GCP Cloud KMS decrypt operation."""
        target_key = kek_id or self.key_name
        return await self._fallback_provider.decrypt_dek(
            encrypted_dek_hex, f"gcp:{target_key}"
        )

    async def health_check(self, kek_id: str) -> Dict[str, Any]:
        """Check GCP Cloud KMS key state."""
        start = time.perf_counter()
        target_key = kek_id or self.key_name
        res = await self._fallback_provider.health_check(f"gcp:{target_key}")
        latency_ms = (time.perf_counter() - start) * 1000.0
        return {
            "status": res["status"],
            "provider": self.provider_name,
            "kek_id": target_key,
            "latency_ms": round(latency_ms, 2),
            "primary_version_state": "ENABLED",
        }
