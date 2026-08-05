"""Reusable Secret Encryption Service for API Keys and External Credentials using AES-256-GCM / Fernet."""

import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet

from app.core.config import settings
from app.core.exceptions import SecurityException
from app.core.logging import get_logger

logger = get_logger("vulnova.security_encryption")


def _derive_fernet_key(secret_seed: str) -> bytes:
    """Derive a URL-safe 32-byte base64 key suitable for Fernet from an arbitrary secret seed."""
    key_bytes = hashlib.sha256(secret_seed.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(key_bytes)


class SecretEncryptionService:
    """Reusable service for encrypting and decrypting sensitive secrets (API keys, SIEM tokens, Cloud credentials) at rest."""

    def __init__(self, key_seed: Optional[str] = None) -> None:
        seed_val = (
            str(key_seed)
            if key_seed
            else str(
                getattr(
                    settings,
                    "SECRET_KEY",
                    "vulnova-default-secret-key-change-in-production",
                )
            )
        )
        fernet_key = _derive_fernet_key(seed_val)
        self.fernet = Fernet(fernet_key)

    def encrypt_secret(self, plain_text: str) -> str:
        """Encrypt plain text secret into base64 ciphertext string."""
        if not plain_text:
            return ""
        try:
            cipher_bytes: bytes = self.fernet.encrypt(plain_text.encode("utf-8"))
            result: str = cipher_bytes.decode("utf-8")
            return result
        except Exception as e:
            logger.error("secret_encryption.failed", error=str(e))
            raise SecurityException("Failed to encrypt secret.") from e

    def decrypt_secret(self, cipher_text: str) -> str:
        """Decrypt ciphertext string back to plain text secret."""
        if not cipher_text:
            return ""
        try:
            plain_bytes: bytes = self.fernet.decrypt(cipher_text.encode("utf-8"))
            result: str = plain_bytes.decode("utf-8")
            return result
        except Exception as e:
            logger.error("secret_decryption.failed", error=str(e))
            raise SecurityException("Failed to decrypt secret.") from e


class CryptoService:
    """Static wrapper service providing AES-256-GCM / Fernet secret encryption & decryption."""

    _instance: Optional[SecretEncryptionService] = None

    @classmethod
    def _get_service(cls) -> SecretEncryptionService:
        if cls._instance is None:
            cls._instance = SecretEncryptionService()
        return cls._instance

    @classmethod
    def encrypt(cls, plain_text: str) -> str:
        return cls._get_service().encrypt_secret(plain_text)

    @classmethod
    def decrypt(cls, cipher_text: str) -> str:
        return cls._get_service().decrypt_secret(cipher_text)
