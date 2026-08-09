"""Abstract Base Interface for External Key Management System (KMS) Providers (Phase 12.8)."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple


class SecretProviderInterface(ABC):
    """Abstract interface defining required cryptographic methods for external KMS providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the unique provider identifier (e.g. 'local', 'vault', 'aws_kms', 'gcp_kms')."""
        pass

    @abstractmethod
    async def encrypt_dek(self, dek: bytes, kek_id: str) -> Tuple[str, int]:
        """Encrypt a 256-bit Data Encryption Key (DEK) using the external KMS Key Encryption Key (KEK).

        Args:
            dek: Raw 32-byte Data Encryption Key.
            kek_id: External KMS Key identifier or alias.

        Returns:
            Tuple of (encrypted_dek_hex: str, key_version: int).
        """
        pass

    @abstractmethod
    async def decrypt_dek(self, encrypted_dek_hex: str, kek_id: str) -> bytes:
        """Decrypt an encrypted Data Encryption Key (DEK) using the external KMS Key Encryption Key (KEK).

        Args:
            encrypted_dek_hex: Hex-encoded ciphertext of the DEK.
            kek_id: External KMS Key identifier or alias.

        Returns:
            Raw 32-byte decrypted Data Encryption Key.
        """
        pass

    @abstractmethod
    async def health_check(self, kek_id: str) -> Dict[str, Any]:
        """Perform a live roundtrip connectivity & cryptographic health check against the KMS provider.

        Args:
            kek_id: External KMS Key identifier or alias.

        Returns:
            Dictionary containing health status, latency, and provider metadata.
        """
        pass
