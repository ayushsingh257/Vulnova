"""Envelope Encryption Service for Enterprise Secrets Vault (Phase 12.8)."""

import os
from typing import NamedTuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.exceptions import ValidationException
from app.infrastructure.secrets_vault.provider_registry import (
    kms_registry,
)


class EncryptedEnvelope(NamedTuple):
    """Encapsulates the envelope-encrypted payload, encrypted DEK, and cryptographic metadata."""

    encrypted_payload_hex: str
    encrypted_dek_hex: str
    nonce_hex: str
    tag_hex: str
    provider_name: str
    kek_id: str
    key_version: int


class EnvelopeEncryptionService:
    """Enterprise envelope encryption service managing ephemeral Data Encryption Keys (DEKs) and external Key Encryption Keys (KEKs)."""

    @classmethod
    async def encrypt(
        cls,
        plaintext: str,
        kek_id: str,
        provider_name: str | None = None,
    ) -> EncryptedEnvelope:
        """Encrypt plaintext using an ephemeral AES-256 DEK, and encrypt the DEK via external KMS.

        Args:
            plaintext: Plaintext secret string.
            kek_id: Key Encryption Key (KEK) identifier in the target KMS.
            provider_name: KMS provider type ('local', 'vault', 'aws_kms', 'gcp_kms').

        Returns:
            EncryptedEnvelope with encrypted data, encrypted DEK, and GCM parameters.
        """
        if not plaintext:
            raise ValidationException("Plaintext secret value cannot be empty.")

        provider = kms_registry.get_provider(provider_name)

        # 1. Generate ephemeral 256-bit (32 bytes) Data Encryption Key (DEK)
        dek = os.urandom(32)

        # 2. Encrypt plaintext payload with DEK using AES-256-GCM
        nonce = os.urandom(12)
        aesgcm = AESGCM(dek)
        aad = kek_id.encode("utf-8")
        raw_ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), aad)

        # Separate ciphertext and 16-byte authentication tag
        payload_bytes = raw_ciphertext[:-16]
        tag_bytes = raw_ciphertext[-16:]

        # 3. Encrypt the DEK using the external KMS Key Encryption Key (KEK)
        encrypted_dek_hex, key_version = await provider.encrypt_dek(dek, kek_id)

        return EncryptedEnvelope(
            encrypted_payload_hex=payload_bytes.hex(),
            encrypted_dek_hex=encrypted_dek_hex,
            nonce_hex=nonce.hex(),
            tag_hex=tag_bytes.hex(),
            provider_name=provider.provider_name,
            kek_id=kek_id,
            key_version=key_version,
        )

    @classmethod
    async def decrypt(
        cls,
        encrypted_payload_hex: str,
        encrypted_dek_hex: str,
        nonce_hex: str,
        tag_hex: str,
        kek_id: str,
        provider_name: str,
    ) -> str:
        """Decrypt an envelope-encrypted secret using the external KMS and decrypted DEK.

        Args:
            encrypted_payload_hex: Hex string of the payload ciphertext.
            encrypted_dek_hex: Hex string of the encrypted DEK.
            nonce_hex: Hex string of the 12-byte GCM nonce.
            tag_hex: Hex string of the 16-byte GCM authentication tag.
            kek_id: KMS Key Encryption Key (KEK) identifier.
            provider_name: KMS provider used for original encryption.

        Returns:
            Decrypted plaintext secret string.
        """
        provider = kms_registry.get_provider(provider_name)

        # 1. Decrypt the Data Encryption Key (DEK) using the external KMS
        dek = await provider.decrypt_dek(encrypted_dek_hex, kek_id)

        # 2. Reconstruct raw ciphertext with authentication tag
        try:
            nonce = bytes.fromhex(nonce_hex)
            payload = bytes.fromhex(encrypted_payload_hex)
            tag = bytes.fromhex(tag_hex)
            raw_ciphertext = payload + tag

            # 3. Decrypt payload using decrypted DEK
            aesgcm = AESGCM(dek)
            aad = kek_id.encode("utf-8")
            plaintext_bytes = aesgcm.decrypt(nonce, raw_ciphertext, aad)
            return plaintext_bytes.decode("utf-8")
        except Exception as exc:
            raise ValidationException(
                f"Failed to decrypt secret payload with decrypted DEK: {str(exc)}"
            ) from exc
