"""Plugin Trust & Publisher Lifecycle Governance Service (Phase 12.7)."""

import hashlib
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.core.logging import get_logger
from app.infrastructure.database.models.plugin_security import (
    PluginTrustedPublisherModel,
)
from app.infrastructure.plugin_security.dto import (
    PublisherTrustStatus,
    RegisterPublisherRequestDTO,
    TrustedPublisherDTO,
)

logger = get_logger("vulnova.plugin_trust_service")


class PluginTrustService:
    """Manages trusted publisher registry, public keys, trust states, and key rotations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_service = AuditLogService(session)

    @staticmethod
    def _validate_and_fingerprint_key(public_key_hex: str) -> str:
        """Validate Ed25519 public key hex format and return SHA-256 fingerprint."""
        cleaned = public_key_hex.strip()
        try:
            raw = bytes.fromhex(cleaned)
        except ValueError as err:
            raise ValidationException(
                "Public key must be a valid hexadecimal string."
            ) from err

        if len(raw) != 32:
            raise ValidationException(
                f"Ed25519 public key must be exactly 32 bytes (64 hex characters), received {len(raw)} bytes."
            )

        return hashlib.sha256(raw).hexdigest()

    async def register_trusted_publisher(
        self,
        req: RegisterPublisherRequestDTO,
        organization_id: UUID,
        actor_user_id: Optional[UUID] = None,
    ) -> TrustedPublisherDTO:
        """Register a new trusted publisher with verified Ed25519 public key."""
        fingerprint = self._validate_and_fingerprint_key(req.public_key_hex)
        now = datetime.now(timezone.utc)

        # Check existing publisher
        stmt = select(PluginTrustedPublisherModel).where(
            PluginTrustedPublisherModel.organization_id == organization_id,
            PluginTrustedPublisherModel.publisher_id == req.publisher_id,
        )
        res = await self.session.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            # Re-activate or update
            existing.publisher_name = req.publisher_name
            existing.public_key_hex = req.public_key_hex.strip()
            existing.public_key_fingerprint = fingerprint
            existing.trust_status = PublisherTrustStatus.TRUSTED.value
            existing.contact_email = req.contact_email
            existing.verified_at = now
            existing.revoked_at = None
            existing.revocation_reason = None
            await self.session.flush()
            model = existing
        else:
            model = PluginTrustedPublisherModel(
                id=uuid4(),
                organization_id=organization_id,
                publisher_id=req.publisher_id,
                publisher_name=req.publisher_name,
                public_key_hex=req.public_key_hex.strip(),
                public_key_fingerprint=fingerprint,
                trust_status=PublisherTrustStatus.TRUSTED.value,
                contact_email=req.contact_email,
                verified_at=now,
                created_at=now,
            )
            self.session.add(model)
            await self.session.flush()

        await self.audit_service.record_event(
            organization_id=organization_id,
            action="plugin.publisher_trusted",
            resource_type="plugin_publisher",
            resource_id=req.publisher_id,
            actor_user_id=actor_user_id,
            details={
                "publisher_name": req.publisher_name,
                "fingerprint": fingerprint,
                "contact_email": req.contact_email,
            },
        )

        logger.info(
            "plugin_trust.publisher_registered",
            publisher_id=req.publisher_id,
            fingerprint=fingerprint,
            org_id=str(organization_id),
        )

        return self._to_dto(model)

    async def list_trusted_publishers(
        self,
        organization_id: UUID,
        status: Optional[str] = None,
    ) -> List[TrustedPublisherDTO]:
        """List trusted publishers for an organization, optionally filtered by status."""
        stmt = select(PluginTrustedPublisherModel).where(
            PluginTrustedPublisherModel.organization_id == organization_id
        )
        if status:
            stmt = stmt.where(
                PluginTrustedPublisherModel.trust_status == status.upper()
            )

        stmt = stmt.order_by(PluginTrustedPublisherModel.created_at.desc())
        res = await self.session.execute(stmt)
        publishers = res.scalars().all()
        return [self._to_dto(p) for p in publishers]

    async def get_publisher(
        self,
        publisher_id: str,
        organization_id: UUID,
    ) -> Optional[TrustedPublisherDTO]:
        """Fetch a publisher by publisher_id."""
        stmt = select(PluginTrustedPublisherModel).where(
            PluginTrustedPublisherModel.organization_id == organization_id,
            PluginTrustedPublisherModel.publisher_id == publisher_id,
        )
        res = await self.session.execute(stmt)
        publisher = res.scalar_one_or_none()
        return self._to_dto(publisher) if publisher else None

    async def revoke_publisher(
        self,
        publisher_id: str,
        organization_id: UUID,
        actor_user_id: Optional[UUID] = None,
        reason: str = "Revoked by security administrator",
    ) -> TrustedPublisherDTO:
        """Revoke trust for a plugin publisher, blocking all signed plugins from executing."""
        stmt = select(PluginTrustedPublisherModel).where(
            PluginTrustedPublisherModel.organization_id == organization_id,
            PluginTrustedPublisherModel.publisher_id == publisher_id,
        )
        res = await self.session.execute(stmt)
        publisher = res.scalar_one_or_none()

        if not publisher:
            raise ResourceNotFoundException(
                f"Trusted publisher '{publisher_id}' not found."
            )

        now = datetime.now(timezone.utc)
        publisher.trust_status = PublisherTrustStatus.REVOKED.value
        publisher.revoked_at = now
        publisher.revocation_reason = reason
        await self.session.flush()

        await self.audit_service.record_event(
            organization_id=organization_id,
            action="plugin.publisher_revoked",
            resource_type="plugin_publisher",
            resource_id=publisher_id,
            actor_user_id=actor_user_id,
            details={
                "reason": reason,
                "fingerprint": publisher.public_key_fingerprint,
            },
        )

        logger.warning(
            "plugin_trust.publisher_revoked",
            publisher_id=publisher_id,
            reason=reason,
            org_id=str(organization_id),
        )

        return self._to_dto(publisher)

    async def rotate_publisher_key(
        self,
        publisher_id: str,
        new_public_key_hex: str,
        organization_id: UUID,
        actor_user_id: Optional[UUID] = None,
        reason: Optional[str] = None,
    ) -> TrustedPublisherDTO:
        """Rotate a publisher's public key while preserving trust history."""
        new_fingerprint = self._validate_and_fingerprint_key(new_public_key_hex)
        stmt = select(PluginTrustedPublisherModel).where(
            PluginTrustedPublisherModel.organization_id == organization_id,
            PluginTrustedPublisherModel.publisher_id == publisher_id,
        )
        res = await self.session.execute(stmt)
        publisher = res.scalar_one_or_none()

        if not publisher:
            raise ResourceNotFoundException(f"Publisher '{publisher_id}' not found.")

        now = datetime.now(timezone.utc)
        old_fingerprint = publisher.public_key_fingerprint
        publisher.public_key_hex = new_public_key_hex.strip()
        publisher.public_key_fingerprint = new_fingerprint
        publisher.trust_status = PublisherTrustStatus.TRUSTED.value
        publisher.verified_at = now
        publisher.revoked_at = None
        publisher.revocation_reason = None
        await self.session.flush()

        await self.audit_service.record_event(
            organization_id=organization_id,
            action="plugin.publisher_key_rotated",
            resource_type="plugin_publisher",
            resource_id=publisher_id,
            actor_user_id=actor_user_id,
            details={
                "old_fingerprint": old_fingerprint,
                "new_fingerprint": new_fingerprint,
                "reason": reason or "Scheduled key rotation",
            },
        )

        return self._to_dto(publisher)

    @staticmethod
    def _to_dto(model: PluginTrustedPublisherModel) -> TrustedPublisherDTO:
        return TrustedPublisherDTO(
            id=model.id,
            organization_id=model.organization_id,
            publisher_id=model.publisher_id,
            publisher_name=model.publisher_name,
            public_key_hex=model.public_key_hex,
            public_key_fingerprint=model.public_key_fingerprint,
            trust_status=PublisherTrustStatus(model.trust_status),
            contact_email=model.contact_email,
            verified_at=model.verified_at,
            revoked_at=model.revoked_at,
            revocation_reason=model.revocation_reason,
            created_at=model.created_at,
        )
