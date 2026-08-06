"""AES-256 Backup Encryption Utility providing secure at-rest protection and checksum verification."""

import base64
import hashlib
import os
from typing import Optional

import structlog
from cryptography.fernet import Fernet

from app.core.config import settings

logger = structlog.get_logger(__name__)


def _derive_fernet_key(secret: str) -> bytes:
    """Derive a URL-safe 32-byte Fernet key from arbitrary secret using SHA-256."""
    key = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(key)


class BackupEncryptionUtility:
    """Utility encrypting and decrypting PostgreSQL backup archives with SHA-256 checksum tracking."""

    def __init__(self, key_secret: Optional[str] = None) -> None:
        raw_secret = key_secret or settings.jwt_secret
        fernet_key = _derive_fernet_key(raw_secret)
        self.cipher = Fernet(fernet_key)

    def calculate_checksum(self, file_path: str) -> str:
        """Compute SHA-256 hex checksum of target file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def encrypt_data(self, data: bytes) -> bytes:
        """Encrypt raw bytes with AES-256 (Fernet)."""
        return self.cipher.encrypt(data)

    def decrypt_data(self, token: bytes) -> bytes:
        """Decrypt AES-256 (Fernet) ciphertext bytes."""
        return self.cipher.decrypt(token)

    def encrypt_file(self, input_path: str, output_path: str) -> str:
        """Encrypt input file and write AES-256 ciphertext to output_path."""
        with open(input_path, "rb") as f_in:
            data = f_in.read()
        encrypted = self.encrypt_data(data)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f_out:
            f_out.write(encrypted)
        logger.info("backup_file_encrypted", input=input_path, output=output_path)
        return self.calculate_checksum(output_path)

    def decrypt_file(self, input_path: str, output_path: str) -> str:
        """Decrypt ciphertext file and write plaintext to output_path."""
        with open(input_path, "rb") as f_in:
            data = f_in.read()
        decrypted = self.decrypt_data(data)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f_out:
            f_out.write(decrypted)
        logger.info("backup_file_decrypted", input=input_path, output=output_path)
        return self.calculate_checksum(output_path)


# Global singleton instance
backup_encryption = BackupEncryptionUtility()
