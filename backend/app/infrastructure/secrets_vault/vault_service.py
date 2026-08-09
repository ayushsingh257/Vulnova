"""Enterprise Secret Vault Service (Phase 12.8)."""

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.audit_logs.services import AuditLogService
from app.core.config import settings
from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.infrastructure.database.models.secret_vault import (
    SecretAccessPolicyModel,
    SecretRotationPolicyModel,
    SecretVaultEntryModel,
)
from app.infrastructure.secrets_vault.dto import (
    CreateSecretRequestDTO,
    SecretDecryptedDTO,
    SecretResponseDTO,
    SecretStatus,
    SecretType,
)
from app.infrastructure.secrets_vault.envelope_encryption import (
    EnvelopeEncryptionService,
)


class SecretVaultService:
    """Core enterprise secrets vault management service with envelope encryption and governance."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_service = AuditLogService(session)

    def _mask_secret(self, plaintext: str) -> str:
        """Create a safe masked string for non-sensitive UI and log previews."""
        if len(plaintext) >= 8:
            return f"********{plaintext[-4:]}"
        return "********"

    def _to_response_dto(
        self,
        entry: SecretVaultEntryModel,
        rotation_policy: Optional[SecretRotationPolicyModel] = None,
    ) -> SecretResponseDTO:
        """Convert database model into a public SecretResponseDTO."""
        interval_days = (
            rotation_policy.rotation_interval_days
            if rotation_policy
            else entry.metadata_json.get("rotation_interval_days", 90)
        )
        next_due = (
            rotation_policy.next_rotation_due
            if rotation_policy
            else entry.metadata_json.get("next_rotation_due")
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
            rotation_interval_days=interval_days,
            last_rotated_at=entry.last_rotated_at,
            next_rotation_due=next_due,
            expires_at=entry.expires_at,
            created_at=entry.created_at or datetime.now(timezone.utc),
            updated_at=entry.updated_at or datetime.now(timezone.utc),
        )

    async def store_secret(
        self,
        request: CreateSecretRequestDTO,
        organization_id: UUID,
        actor_user_id: Optional[UUID] = None,
    ) -> SecretResponseDTO:
        """Create and store a new envelope-encrypted enterprise secret."""
        # 1. Check for existing secret with identical name in organization
        existing_stmt = select(SecretVaultEntryModel).where(
            SecretVaultEntryModel.organization_id == organization_id,
            SecretVaultEntryModel.secret_name == request.secret_name,
        )
        res = await self.session.execute(existing_stmt)
        if res.scalar_one_or_none() is not None:
            raise ValidationException(
                f"Secret with name '{request.secret_name}' already exists in this organization."
            )

        now = datetime.now(timezone.utc)
        kek_id = f"org_{organization_id}_kek"

        # 2. Envelope encrypt the secret payload
        envelope = await EnvelopeEncryptionService.encrypt(
            plaintext=request.plaintext_value,
            kek_id=kek_id,
            provider_name=settings.kms_provider,
        )

        # 3. Calculate expiration and next rotation
        expires_at = None
        if request.expires_in_days:
            expires_at = now + timedelta(days=request.expires_in_days)

        rotation_interval = (
            request.rotation_interval_days or settings.secret_default_rotation_days
        )
        next_rotation_due = now + timedelta(days=rotation_interval)

        metadata_dict = dict(request.metadata or {})
        metadata_dict["masked_value"] = self._mask_secret(request.plaintext_value)
        metadata_dict["rotation_interval_days"] = rotation_interval
        metadata_dict["next_rotation_due"] = next_rotation_due.isoformat()

        # 4. Create secret entry model
        entry_id = uuid4()
        entry = SecretVaultEntryModel(
            id=entry_id,
            organization_id=organization_id,
            secret_name=request.secret_name,
            secret_type=request.secret_type.value,
            provider=envelope.provider_name,
            kek_id=envelope.kek_id,
            encrypted_dek_hex=envelope.encrypted_dek_hex,
            encrypted_payload_hex=envelope.encrypted_payload_hex,
            nonce_hex=envelope.nonce_hex,
            tag_hex=envelope.tag_hex,
            key_version=envelope.key_version,
            status=SecretStatus.ACTIVE.value,
            metadata_json=metadata_dict,
            expires_at=expires_at,
            created_at=now,
            updated_at=now,
        )
        self.session.add(entry)

        # 5. Create rotation policy model
        rotation_policy = SecretRotationPolicyModel(
            id=uuid4(),
            organization_id=organization_id,
            secret_id=entry_id,
            rotation_interval_days=rotation_interval,
            auto_rotate=True,
            last_rotation_at=None,
            next_rotation_due=next_rotation_due,
            status="ACTIVE",
            created_at=now,
            updated_at=now,
        )
        self.session.add(rotation_policy)

        # 6. Create default access policy model
        access_policy = SecretAccessPolicyModel(
            id=uuid4(),
            organization_id=organization_id,
            secret_id=entry_id,
            min_role="ADMIN",
            require_approval=False,
            allowed_ip_cidrs=[],
            created_at=now,
        )
        self.session.add(access_policy)

        await self.session.flush()

        # 7. Record immutable audit log
        await self.audit_service.record_event(
            action="secret.created",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            resource_type="secret_vault",
            resource_id=str(entry_id),
            details={
                "secret_name": request.secret_name,
                "secret_type": request.secret_type.value,
                "provider": envelope.provider_name,
                "rotation_interval_days": rotation_interval,
            },
        )

        return self._to_response_dto(entry, rotation_policy)

    async def get_secret_metadata(
        self, secret_id: UUID, organization_id: UUID
    ) -> SecretResponseDTO:
        """Fetch non-sensitive metadata for a stored secret."""
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
        return self._to_response_dto(entry, policy)

    async def access_secret_plaintext(
        self,
        secret_id: UUID,
        organization_id: UUID,
        actor_user_id: Optional[UUID] = None,
        client_ip: Optional[str] = None,
    ) -> SecretDecryptedDTO:
        """Decrypt and return plaintext secret to authorized caller with audit logging."""
        stmt = select(SecretVaultEntryModel).where(
            SecretVaultEntryModel.id == secret_id,
            SecretVaultEntryModel.organization_id == organization_id,
        )
        res = await self.session.execute(stmt)
        entry = res.scalar_one_or_none()
        if not entry:
            raise ResourceNotFoundException(f"Secret with id '{secret_id}' not found.")

        now = datetime.now(timezone.utc)

        # Enforce status rules
        if entry.status == SecretStatus.REVOKED.value:
            raise ValidationException(
                f"Access Denied: Secret '{entry.secret_name}' has been revoked."
            )

        if entry.expires_at and entry.expires_at <= now:
            entry.status = SecretStatus.EXPIRED.value
            await self.session.flush()
            raise ValidationException(
                f"Access Denied: Secret '{entry.secret_name}' has expired."
            )

        # Decrypt secret via envelope encryption pipeline
        plaintext = await EnvelopeEncryptionService.decrypt(
            encrypted_payload_hex=entry.encrypted_payload_hex,
            encrypted_dek_hex=entry.encrypted_dek_hex,
            nonce_hex=entry.nonce_hex,
            tag_hex=entry.tag_hex,
            kek_id=entry.kek_id,
            provider_name=entry.provider,
        )

        # Record access audit event
        await self.audit_service.record_event(
            action="secret.accessed",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            resource_type="secret_vault",
            resource_id=str(secret_id),
            details={
                "secret_name": entry.secret_name,
                "key_version": entry.key_version,
                "client_ip": client_ip,
            },
        )

        return SecretDecryptedDTO(
            id=entry.id,
            secret_name=entry.secret_name,
            secret_type=SecretType(entry.secret_type),
            plaintext_value=plaintext,
            key_version=entry.key_version,
            accessed_at=now,
        )

    async def list_secrets(
        self,
        organization_id: UUID,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[SecretResponseDTO], int]:
        """List secrets metadata for an organization."""
        query = (
            select(SecretVaultEntryModel, SecretRotationPolicyModel)
            .outerjoin(
                SecretRotationPolicyModel,
                SecretVaultEntryModel.id == SecretRotationPolicyModel.secret_id,
            )
            .where(SecretVaultEntryModel.organization_id == organization_id)
        )

        if status:
            query = query.where(SecretVaultEntryModel.status == status.upper())

        count_query = select(func.count(SecretVaultEntryModel.id)).where(
            SecretVaultEntryModel.organization_id == organization_id
        )
        if status:
            count_query = count_query.where(
                SecretVaultEntryModel.status == status.upper()
            )

        total_res = await self.session.execute(count_query)
        total = total_res.scalar_one() or 0

        query = (
            query.order_by(SecretVaultEntryModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.session.execute(query)
        rows = res.all()

        dtos = [self._to_response_dto(entry, policy) for entry, policy in rows]
        return dtos, total

    async def revoke_secret(
        self,
        secret_id: UUID,
        organization_id: UUID,
        actor_user_id: Optional[UUID] = None,
        reason: str = "Administrator revoked secret",
    ) -> SecretResponseDTO:
        """Revoke a secret, immediately preventing future access."""
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
        entry.status = SecretStatus.REVOKED.value
        entry.updated_at = datetime.now(timezone.utc)
        if policy:
            policy.status = "PAUSED"

        await self.session.flush()

        await self.audit_service.record_event(
            action="secret.revoked",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            resource_type="secret_vault",
            resource_id=str(secret_id),
            details={"secret_name": entry.secret_name, "reason": reason},
        )

        return self._to_response_dto(entry, policy)

    async def delete_secret(
        self,
        secret_id: UUID,
        organization_id: UUID,
        actor_user_id: Optional[UUID] = None,
    ) -> bool:
        """Permanently delete a secret from the vault."""
        stmt = select(SecretVaultEntryModel).where(
            SecretVaultEntryModel.id == secret_id,
            SecretVaultEntryModel.organization_id == organization_id,
        )
        res = await self.session.execute(stmt)
        entry = res.scalar_one_or_none()
        if not entry:
            raise ResourceNotFoundException(f"Secret with id '{secret_id}' not found.")

        secret_name = entry.secret_name
        await self.session.delete(entry)
        await self.session.flush()

        await self.audit_service.record_event(
            action="secret.deleted",
            actor_user_id=actor_user_id,
            organization_id=organization_id,
            resource_type="secret_vault",
            resource_id=str(secret_id),
            details={"secret_name": secret_name},
        )

        return True
