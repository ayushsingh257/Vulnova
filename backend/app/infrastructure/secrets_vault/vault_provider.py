"""HashiCorp Vault Transit KMS Provider (Phase 12.8)."""

import base64
import logging
import time
from typing import Any, Dict, Tuple

import httpx

from app.core.config import settings
from app.core.exceptions import ValidationException
from app.infrastructure.secrets_vault.local_provider import (
    LocalDevSecretProvider,
)
from app.infrastructure.secrets_vault.provider_interface import (
    SecretProviderInterface,
)

logger = logging.getLogger(__name__)


class VaultSecretProvider(SecretProviderInterface):
    """HashiCorp Vault KMS Provider using Vault Transit Engine for cryptographic envelope operations."""

    def __init__(
        self,
        vault_addr: str | None = None,
        vault_token: str | None = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.vault_addr = (vault_addr or settings.vault_addr).rstrip("/")
        self.vault_token = vault_token or settings.vault_token
        self.timeout_seconds = timeout_seconds
        self._fallback_provider = LocalDevSecretProvider()

    @property
    def provider_name(self) -> str:
        return "vault"

    async def encrypt_dek(self, dek: bytes, kek_id: str) -> Tuple[str, int]:
        """Encrypt DEK using HashiCorp Vault Transit encrypt endpoint."""
        if not self.vault_token:
            logger.info(
                "Vault token not set; utilizing dev fallback provider for DEK encryption."
            )
            return await self._fallback_provider.encrypt_dek(dek, kek_id)

        key_name = kek_id or settings.vault_transit_key
        url = f"{self.vault_addr}/v1/transit/encrypt/{key_name}"
        headers = {"X-Vault-Token": self.vault_token}
        payload = {"plaintext": base64.b64encode(dek).decode("utf-8")}

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code != 200:
                    raise ValidationException(
                        f"Vault transit encrypt failed with status {res.status_code}: {res.text}"
                    )
                data = res.json().get("data", {})
                ciphertext = data.get("ciphertext", "")
                version = data.get("key_version", 1)
                return ciphertext.encode("utf-8").hex(), version
        except Exception as exc:
            if isinstance(exc, ValidationException):
                raise
            raise ValidationException(
                f"Vault connection error during encrypt: {str(exc)}"
            ) from exc

    async def decrypt_dek(self, encrypted_dek_hex: str, kek_id: str) -> bytes:
        """Decrypt DEK using HashiCorp Vault Transit decrypt endpoint."""
        if not self.vault_token:
            return await self._fallback_provider.decrypt_dek(encrypted_dek_hex, kek_id)

        try:
            ciphertext = bytes.fromhex(encrypted_dek_hex.strip()).decode("utf-8")
        except Exception:
            ciphertext = encrypted_dek_hex

        key_name = kek_id or settings.vault_transit_key
        url = f"{self.vault_addr}/v1/transit/decrypt/{key_name}"
        headers = {"X-Vault-Token": self.vault_token}
        payload = {"ciphertext": ciphertext}

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                res = await client.post(url, headers=headers, json=payload)
                if res.status_code != 200:
                    raise ValidationException(
                        f"Vault transit decrypt failed with status {res.status_code}: {res.text}"
                    )
                data = res.json().get("data", {})
                b64_plain = data.get("plaintext", "")
                return base64.b64decode(b64_plain)
        except Exception as exc:
            if isinstance(exc, ValidationException):
                raise
            raise ValidationException(
                f"Vault connection error during decrypt: {str(exc)}"
            ) from exc

    async def health_check(self, kek_id: str) -> Dict[str, Any]:
        """Check Vault health status."""
        start = time.perf_counter()
        if not self.vault_token:
            res = await self._fallback_provider.health_check(kek_id)
            res["provider"] = "vault (emulated)"
            return res

        url = f"{self.vault_addr}/v1/sys/health"
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                http_res = await client.get(url)
                latency_ms = (time.perf_counter() - start) * 1000.0
                is_healthy = http_res.status_code in (200, 429, 472, 473)
                return {
                    "status": "healthy" if is_healthy else "degraded",
                    "provider": self.provider_name,
                    "vault_addr": self.vault_addr,
                    "kek_id": kek_id or settings.vault_transit_key,
                    "latency_ms": round(latency_ms, 2),
                    "details": (
                        http_res.json()
                        if http_res.status_code == 200
                        else {"code": http_res.status_code}
                    ),
                }
        except Exception as exc:
            return {
                "status": "unhealthy",
                "provider": self.provider_name,
                "error": str(exc),
                "latency_ms": round((time.perf_counter() - start) * 1000.0, 2),
            }
