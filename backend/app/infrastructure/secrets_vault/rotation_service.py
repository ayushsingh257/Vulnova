"""Automated Secret Rotation Pipeline Service (Phase 12.8)."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.core.config import settings
from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.infrastructure.database.models.secret_vault import (
    SecretRotationPolicyModel,
    SecretVaultEntryModel,
)
from app.infrastructure.secrets_vault.dto import (
    SecretResponseDTO,
    SecretRotationStatusDTO,
    SecretStatus,
    SecretType,
)
from app.infrastructure.secrets_vault.envelope_encryption import (
    EnvelopeEncryptionService,
)


class SecretRotationService:
    """Automated secret rotation engine enforcing 90-day lifecycle governance and DEK re-keying."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_service = AuditLogService(session)

    def _mask_secret(self, plaintext: str) -> str:
        """Create a safe masked string for non-sensitive previews."""
        if len(plaintext) >= 8:
            return f"********{plaintext[-4:]}"
        return "********"

    async def rotate_secret(
        self,
        secret_id: UUID,
        organization_id: UUID,
        new_plaintext_value: Optional[str] = None,
        actor_user_id: Optional[UUID] = None,
        reason: Optional[str] = "Manual rotation requested",
    ) -> SecretResponseDTO:
        """Rotate a secret by generating a fresh DEK and updating encryption metadata."""
        stmt = (
            select(SecretVaultEntryModel, SecretRotationPolicyModel)
            .outerjoin(
                SecretRotationPolicyModel,
                SecretVaultEntryModel.id == SecretRotationPolicyModel.secret_id,
            )
            .where(
                SecretVaultEntryModel.id == secret_id,
                SecretVaultEntryModel.organization_id == organization_id,
            )
        )
        res = await self.session.execute(stmt)
        row = res.first()
        if not row:
            raise ResourceNotFoundException(f"Secret with id '{secret_id}' not found.")

        entry, policy = row
        if entry.status == SecretStatus.REVOKED.value:
            raise ValidationException("Cannot rotate a revoked secret.")

        # 1. Determine plaintext to re-encrypt
        if new_plaintext_value:
            plaintext = new_plaintext_value
        else:
            # Decrypt existing secret payload to re-encrypt with fresh DEK
            plaintext = await EnvelopeEncryptionService.decrypt(
                encrypted_payload_hex=entry.encrypted_payload_hex,
                encrypted_dek_hex=entry.encrypted_dek_hex,
                nonce_hex=entry.nonce_hex,
                tag_hex=entry.tag_hex,
                kek_id=entry.kek_id,
                provider_name=entry.provider,
            )

        now = datetime.now(timezone.utc)

        # 2. Envelope encrypt with fresh DEK
        envelope = await EnvelopeEncryptionService.encrypt(
            plaintext=plaintext,
            kek_id=entry.kek_id,
            provider_name=settings.kms_provider,
        )

        # 3. Update entry model
        entry.encrypted_payload_hex = envelope.encrypted_payload_hex
        entry.encrypted_dek_hex = envelope.encrypted_dek_hex
        entry.nonce_hex = envelope.nonce_hex
        entry.tag_hex = envelope.tag_hex
        entry.provider = envelope.provider_name
        entry.key_version += 1
        entry.status = SecretStatus.ACTIVE.value
        entry.last_rotated_at = now
        entry.updated_at = now

        meta = dict(entry.metadata_json or {})
        if new_plaintext_value:
            meta["masked_value"] = self._mask_secret(new_plaintext_value)
        meta["last_rotation_reason"] = reason

        # 4. Update policy model
        interval = policy.rotation_interval_days if policy else 90
        next_due = now + timedelta(days=interval)
        if policy:
            policy.last_rotation_at = now
            policy.next_rotation_due = next_due
            policy.status = "ACTIVE"
            policy.updated_at = now
            meta["next_rotation_due"] = next_due.isoformat()

        entry.metadata_json = meta
        await self.session.flush()

        # 5. Record rotation audit event
        await self.audit_service.record_event(
            action="secret.rotated",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            resource_type="secret_vault",
            resource_id=str(secret_id),
            details={
                "secret_name": entry.secret_name,
                "new_key_version": entry.key_version,
                "provider": envelope.provider_name,
                "reason": reason,
            },
        )

        return SecretResponseDTO(
            id=entry.id,
            organization_id=entry.organization_id,
            secret_name=entry.secret_name,
            secret_type=SecretType(entry.secret_type),
            provider=entry.provider,
            masked_value=entry.metadata_json.get("masked_value", "********"),
            key_version=entry.key_version,
            status=SecretStatus(entry.status),
            metadata=entry.metadata_json,
            rotation_interval_days=interval,
            last_rotated_at=entry.last_rotated_at,
            next_rotation_due=next_due,
            expires_at=entry.expires_at,
            created_at=entry.created_at or now,
            updated_at=entry.updated_at or now,
        )

    async def check_and_rotate_expired_secrets(
        self, organization_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Scan and automatically rotate secrets due for rotation."""
        now = datetime.now(timezone.utc)
        query = (
            select(SecretVaultEntryModel, SecretRotationPolicyModel)
            .join(
                SecretRotationPolicyModel,
                SecretVaultEntryModel.id == SecretRotationPolicyModel.secret_id,
            )
            .where(
                SecretRotationPolicyModel.auto_rotate == True,  # noqa: E712
                SecretRotationPolicyModel.next_rotation_due <= now,
                SecretVaultEntryModel.status != SecretStatus.REVOKED.value,
            )
        )
        if organization_id:
            query = query.where(
                SecretVaultEntryModel.organization_id == organization_id
            )

        res = await self.session.execute(query)
        due_items = res.all()

        rotated_count = 0
        failed_count = 0
        details: List[Dict[str, Any]] = []

        for entry, _ in due_items:
            try:
                await self.rotate_secret(
                    secret_id=entry.id,
                    organization_id=entry.organization_id,
                    reason="Automated 90-day lifecycle rotation worker",
                )
                rotated_count += 1
                details.append(
                    {
                        "secret_id": str(entry.id),
                        "secret_name": entry.secret_name,
                        "status": "ROTATED",
                    }
                )
            except Exception as exc:
                failed_count += 1
                details.append(
                    {
                        "secret_id": str(entry.id),
                        "secret_name": entry.secret_name,
                        "status": "FAILED",
                        "error": str(exc),
                    }
                )

        return {
            "processed_at": now.isoformat(),
            "rotated_count": rotated_count,
            "failed_count": failed_count,
            "details": details,
        }

    async def get_rotation_posture(
        self, organization_id: UUID
    ) -> SecretRotationStatusDTO:
        """Calculate aggregated rotation health and compliance posture for an organization."""
        now = datetime.now(timezone.utc)
        in_7_days = now + timedelta(days=7)
        in_30_days = now + timedelta(days=30)

        # Total secrets in organization
        total_stmt = select(func.count(SecretVaultEntryModel.id)).where(
            SecretVaultEntryModel.organization_id == organization_id,
            SecretVaultEntryModel.status != SecretStatus.REVOKED.value,
        )
        total_res = await self.session.execute(total_stmt)
        total_secrets = total_res.scalar_one() or 0

        # Active rotation policies
        active_policies_stmt = (
            select(SecretRotationPolicyModel)
            .join(
                SecretVaultEntryModel,
                SecretRotationPolicyModel.secret_id == SecretVaultEntryModel.id,
            )
            .where(
                SecretVaultEntryModel.organization_id == organization_id,
                SecretVaultEntryModel.status != SecretStatus.REVOKED.value,
                SecretRotationPolicyModel.status == "ACTIVE",
            )
        )
        policies_res = await self.session.execute(active_policies_stmt)
        policies = policies_res.scalars().all()

        active_count = len(policies)
        due_7 = sum(1 for p in policies if now < p.next_rotation_due <= in_7_days)
        due_30 = sum(1 for p in policies if now < p.next_rotation_due <= in_30_days)
        overdue = sum(1 for p in policies if p.next_rotation_due <= now)

        return SecretRotationStatusDTO(
            total_secrets=total_secrets,
            active_rotations=active_count,
            due_in_7_days=due_7,
            due_in_30_days=due_30,
            overdue_rotations=overdue,
            active_provider=settings.kms_provider,
        )
