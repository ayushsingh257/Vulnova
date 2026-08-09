"""Cryptographic Ed25519 Plugin Signature Verification Service (Phase 12.7)."""

import hashlib
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.core.logging import get_logger
from app.infrastructure.database.models.plugin_security import (
    PluginSignatureModel,
    PluginTrustedPublisherModel,
)
from app.infrastructure.plugin_security.dto import (
    PluginManifestDTO,
    PluginSignatureVerificationResultDTO,
    PluginVerificationStatus,
    PublisherTrustStatus,
)

logger = get_logger("vulnova.plugin_signature_service")


class PluginSignatureService:
    """Handles Ed25519 digital signature validation and publisher key fingerprinting."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_service = AuditLogService(session)

    @staticmethod
    def calculate_key_fingerprint(public_key_hex: str) -> str:
        """Compute SHA-256 digest fingerprint of an Ed25519 public key."""
        raw_key = bytes.fromhex(public_key_hex.strip())
        return hashlib.sha256(raw_key).hexdigest()

    @staticmethod
    def get_canonical_bytes(manifest: PluginManifestDTO) -> bytes:
        """Generate deterministic canonical byte representation of plugin manifest for signing."""
        sorted_caps = ",".join(sorted(c.value for c in manifest.capabilities))
        canonical_str = (
            f"plugin_id:{manifest.plugin_id}|"
            f"version:{manifest.version}|"
            f"publisher_id:{manifest.publisher_id}|"
            f"package_hash:{manifest.package_hash}|"
            f"capabilities:{sorted_caps}"
        )
        return canonical_str.encode("utf-8")

    @staticmethod
    def sign_manifest(
        manifest: PluginManifestDTO, private_key: ed25519.Ed25519PrivateKey
    ) -> str:
        """Utility to sign canonical manifest bytes with an Ed25519 private key (returns hex)."""
        canonical_bytes = PluginSignatureService.get_canonical_bytes(manifest)
        sig_bytes = private_key.sign(canonical_bytes)
        return sig_bytes.hex()

    async def verify_plugin_signature(
        self,
        manifest: PluginManifestDTO,
        signature_hex: str,
        organization_id: UUID,
        actor_user_id: Optional[UUID] = None,
    ) -> PluginSignatureVerificationResultDTO:
        """Verify the cryptographic signature of a plugin manifest against the trusted publisher registry."""
        now = datetime.now(timezone.utc)

        # ── Step 1: Look up Publisher in Registry ──
        stmt = select(PluginTrustedPublisherModel).where(
            PluginTrustedPublisherModel.organization_id == organization_id,
            PluginTrustedPublisherModel.publisher_id == manifest.publisher_id,
        )
        res = await self.session.execute(stmt)
        publisher = res.scalar_one_or_none()

        if not publisher:
            logger.warning(
                "plugin_signature.unknown_publisher",
                plugin_id=manifest.plugin_id,
                publisher_id=manifest.publisher_id,
            )
            result = PluginSignatureVerificationResultDTO(
                plugin_id=manifest.plugin_id,
                publisher_id=manifest.publisher_id,
                public_key_fingerprint=None,
                is_valid=False,
                verification_status=PluginVerificationStatus.UNKNOWN_PUBLISHER,
                trust_status=PublisherTrustStatus.UNTRUSTED,
                verified_at=now,
                error_message=f"Publisher '{manifest.publisher_id}' is not registered as a trusted publisher.",
            )
            await self._record_verification_result(
                organization_id, manifest, result, signature_hex, actor_user_id
            )
            return result

        fingerprint = publisher.public_key_fingerprint

        # ── Step 2: Check Publisher Trust Status ──
        if publisher.trust_status == PublisherTrustStatus.REVOKED.value:
            logger.warning(
                "plugin_signature.revoked_publisher",
                plugin_id=manifest.plugin_id,
                publisher_id=manifest.publisher_id,
                reason=publisher.revocation_reason,
            )
            result = PluginSignatureVerificationResultDTO(
                plugin_id=manifest.plugin_id,
                publisher_id=manifest.publisher_id,
                public_key_fingerprint=fingerprint,
                is_valid=False,
                verification_status=PluginVerificationStatus.REVOKED_PUBLISHER,
                trust_status=PublisherTrustStatus.REVOKED,
                verified_at=now,
                error_message=f"Publisher '{manifest.publisher_id}' has been revoked: {publisher.revocation_reason}",
            )
            await self._record_verification_result(
                organization_id, manifest, result, signature_hex, actor_user_id
            )
            return result

        # ── Step 3: Perform Cryptographic Ed25519 Verification ──
        try:
            public_key_bytes = bytes.fromhex(publisher.public_key_hex.strip())
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
            sig_bytes = bytes.fromhex(signature_hex.strip())
            canonical_bytes = self.get_canonical_bytes(manifest)

            public_key.verify(sig_bytes, canonical_bytes)
            sig_valid = True
            error_msg = None
            ver_status = PluginVerificationStatus.VERIFIED
            trust_status = PublisherTrustStatus.TRUSTED
        except (InvalidSignature, ValueError, Exception) as exc:
            sig_valid = False
            error_msg = f"Cryptographic signature verification failed: {str(exc)}"
            ver_status = PluginVerificationStatus.INVALID_SIGNATURE
            trust_status = PublisherTrustStatus.UNTRUSTED
            logger.warning(
                "plugin_signature.invalid_signature",
                plugin_id=manifest.plugin_id,
                publisher_id=manifest.publisher_id,
                error=str(exc),
            )

        result = PluginSignatureVerificationResultDTO(
            plugin_id=manifest.plugin_id,
            publisher_id=manifest.publisher_id,
            public_key_fingerprint=fingerprint,
            is_valid=sig_valid,
            verification_status=ver_status,
            trust_status=trust_status,
            verified_at=now,
            details={
                "name": manifest.name,
                "version": manifest.version,
                "package_hash": manifest.package_hash,
                "capabilities": [c.value for c in manifest.capabilities],
            },
            error_message=error_msg,
        )

        await self._record_verification_result(
            organization_id, manifest, result, signature_hex, actor_user_id
        )
        return result

    async def _record_verification_result(
        self,
        organization_id: UUID,
        manifest: PluginManifestDTO,
        result: PluginSignatureVerificationResultDTO,
        signature_hex: str,
        actor_user_id: Optional[UUID],
    ) -> None:
        """Persist verification record and record audit log event."""
        sig_model = PluginSignatureModel(
            id=uuid4(),
            organization_id=organization_id,
            plugin_id=manifest.plugin_id,
            publisher_id=manifest.publisher_id,
            signature_hex=signature_hex,
            public_key_fingerprint=result.public_key_fingerprint or "unknown",
            verification_status=result.verification_status.value,
            verified_at=result.verified_at,
            details_json=result.details,
            created_at=result.verified_at,
        )
        self.session.add(sig_model)
        await self.session.flush()

        action = (
            "plugin.signature_verified"
            if result.is_valid
            else "plugin.signature_failed"
        )
        await self.audit_service.record_event(
            organization_id=organization_id,
            action=action,
            resource_type="plugin_signature",
            resource_id=manifest.plugin_id,
            actor_user_id=actor_user_id,
            details={
                "publisher_id": manifest.publisher_id,
                "status": result.verification_status.value,
                "is_valid": result.is_valid,
                "error": result.error_message,
            },
        )
