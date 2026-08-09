"""Local Development & Testing KMS Provider (Phase 12.8)."""

import hashlib
import os
import time
from typing import Any, Dict, Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings
from app.core.exceptions import ValidationException
from app.infrastructure.secrets_vault.provider_interface import (
    SecretProviderInterface,
)


class LocalDevSecretProvider(SecretProviderInterface):
    """Zero-dependency local KMS provider using HKDF-derived AES-256-GCM master keys for development and tests."""

    @property
    def provider_name(self) -> str:
        return "local"

    def _derive_kek(self, kek_id: str) -> bytes:
        """Derive deterministic 256-bit KEK from kek_id and system master secret."""
        seed = f"{settings.jwt_secret}:{kek_id}:vulnova-kms-v1".encode("utf-8")
        return hashlib.sha256(seed).digest()

    async def encrypt_dek(self, dek: bytes, kek_id: str) -> Tuple[str, int]:
        """Encrypt DEK using AES-256-GCM with derived local KEK."""
        if len(dek) != 32:
            raise ValidationException(f"DEK must be exactly 32 bytes (got {len(dek)})")

        kek = self._derive_kek(kek_id)
        aesgcm = AESGCM(kek)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, dek, kek_id.encode("utf-8"))
        # Combine nonce (12 bytes) + ciphertext (includes 16-byte tag)
        packed = nonce + ciphertext
        return packed.hex(), 1

    async def decrypt_dek(self, encrypted_dek_hex: str, kek_id: str) -> bytes:
        """Decrypt encrypted DEK using local KEK."""
        try:
            packed = bytes.fromhex(encrypted_dek_hex.strip())
            if len(packed) < 28:
                raise ValidationException("Invalid encrypted DEK length")

            nonce = packed[:12]
            ciphertext = packed[12:]
            kek = self._derive_kek(kek_id)
            aesgcm = AESGCM(kek)
            dek = aesgcm.decrypt(nonce, ciphertext, kek_id.encode("utf-8"))
            return dek
        except Exception as exc:
            raise ValidationException(f"Failed to decrypt DEK: {str(exc)}") from exc

    async def health_check(self, kek_id: str) -> Dict[str, Any]:
        """Perform cryptographic roundtrip health check."""
        start = time.perf_counter()
        test_dek = os.urandom(32)
        enc_hex, version = await self.encrypt_dek(test_dek, kek_id)
        dec_dek = await self.decrypt_dek(enc_hex, kek_id)
        latency_ms = (time.perf_counter() - start) * 1000.0

        is_valid = test_dek == dec_dek
        return {
            "status": "healthy" if is_valid else "unhealthy",
            "provider": self.provider_name,
            "kek_id": kek_id,
            "latency_ms": round(latency_ms, 2),
            "key_version": version,
        }
