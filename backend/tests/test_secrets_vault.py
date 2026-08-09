"""Unit and Integration Tests for Phase 12.8 Enterprise Secrets Vault & KMS Credential Governance Architecture."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.infrastructure.database.models.secret_vault import (
    SecretAccessPolicyModel,
    SecretRotationPolicyModel,
    SecretVaultEntryModel,
)
from app.infrastructure.secrets_vault.aws_kms_provider import (
    AWSKMSSecretProvider,
)
from app.infrastructure.secrets_vault.dto import (
    CreateSecretRequestDTO,
    SecretStatus,
    SecretType,
)
from app.infrastructure.secrets_vault.envelope_encryption import (
    EnvelopeEncryptionService,
)
from app.infrastructure.secrets_vault.gcp_kms_provider import (
    GCPKMSSecretProvider,
)
from app.infrastructure.secrets_vault.kms_health_service import (
    KMSHealthService,
)
from app.infrastructure.secrets_vault.local_provider import (
    LocalDevSecretProvider,
)
from app.infrastructure.secrets_vault.provider_registry import (
    KMSProviderRegistry,
    kms_registry,
)
from app.infrastructure.secrets_vault.rotation_service import (
    SecretRotationService,
)
from app.infrastructure.secrets_vault.vault_provider import (
    VaultSecretProvider,
)
from app.infrastructure.secrets_vault.vault_service import (
    SecretVaultService,
)


@pytest.fixture
def anyio_backend() -> str:
    """Specify anyio backend."""
    return "asyncio"


@pytest.fixture
def mock_session() -> AsyncMock:
    """Provide a mock AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.delete = AsyncMock()
    return session


# ── Envelope Encryption Tests ──────────────────────────────────────────


@pytest.mark.anyio
async def test_envelope_encryption_roundtrip() -> None:
    """Test full envelope encryption and decryption roundtrip using Local KMS."""
    plaintext = "super_secret_production_api_key_12345!@#"
    kek_id = "test_org_kek_1"

    envelope = await EnvelopeEncryptionService.encrypt(
        plaintext=plaintext,
        kek_id=kek_id,
        provider_name="local",
    )

    assert envelope.encrypted_payload_hex is not None
    assert envelope.encrypted_dek_hex is not None
    assert envelope.nonce_hex is not None
    assert envelope.tag_hex is not None
    assert envelope.provider_name == "local"
    assert envelope.key_version == 1

    decrypted = await EnvelopeEncryptionService.decrypt(
        encrypted_payload_hex=envelope.encrypted_payload_hex,
        encrypted_dek_hex=envelope.encrypted_dek_hex,
        nonce_hex=envelope.nonce_hex,
        tag_hex=envelope.tag_hex,
        kek_id=kek_id,
        provider_name="local",
    )

    assert decrypted == plaintext


@pytest.mark.anyio
async def test_envelope_encryption_empty_plaintext_rejected() -> None:
    """Test that empty plaintext strings are rejected with ValidationException."""
    with pytest.raises(
        ValidationException, match="Plaintext secret value cannot be empty"
    ):
        await EnvelopeEncryptionService.encrypt(
            plaintext="",
            kek_id="test_kek",
            provider_name="local",
        )


@pytest.mark.anyio
async def test_envelope_encryption_tampered_payload_fails() -> None:
    """Test that tampering with encrypted payload or tag fails decryption."""
    plaintext = "critical_database_password_999"
    kek_id = "test_org_kek_2"

    envelope = await EnvelopeEncryptionService.encrypt(
        plaintext=plaintext,
        kek_id=kek_id,
        provider_name="local",
    )

    # Tamper with the ciphertext
    tampered_payload = envelope.encrypted_payload_hex[:-4] + "0000"

    with pytest.raises(ValidationException, match="Failed to decrypt secret payload"):
        await EnvelopeEncryptionService.decrypt(
            encrypted_payload_hex=tampered_payload,
            encrypted_dek_hex=envelope.encrypted_dek_hex,
            nonce_hex=envelope.nonce_hex,
            tag_hex=envelope.tag_hex,
            kek_id=kek_id,
            provider_name="local",
        )


# ── KMS Providers & Registry Tests ─────────────────────────────────────


def test_kms_provider_registry_defaults() -> None:
    """Test that KMS provider registry initializes with all required providers."""
    registry = KMSProviderRegistry()
    supported = registry.list_supported_providers()
    assert "local" in supported
    assert "vault" in supported
    assert "aws_kms" in supported
    assert "gcp_kms" in supported

    default_prov = registry.get_provider()
    assert default_prov.provider_name in ("local", "vault", "aws_kms", "gcp_kms")


@pytest.mark.anyio
async def test_local_dev_kms_provider_health() -> None:
    """Test local development KMS health check probe."""
    provider = LocalDevSecretProvider()
    res = await provider.health_check("test_kek_health")
    assert res["status"] == "healthy"
    assert res["provider"] == "local"
    assert res["latency_ms"] >= 0.0


@pytest.mark.anyio
async def test_aws_kms_provider_roundtrip() -> None:
    """Test AWS KMS provider envelope encryption driver."""
    provider = AWSKMSSecretProvider(
        key_id="alias/vulnova-test", region_name="us-west-2"
    )
    assert provider.provider_name == "aws_kms"

    test_dek = b"12345678901234567890123456789012"  # 32 bytes
    enc_hex, version = await provider.encrypt_dek(test_dek, "alias/vulnova-test")
    dec_dek = await provider.decrypt_dek(enc_hex, "alias/vulnova-test")
    assert dec_dek == test_dek

    health = await provider.health_check("alias/vulnova-test")
    assert health["status"] == "healthy"
    assert health["region"] == "us-west-2"


@pytest.mark.anyio
async def test_gcp_kms_provider_roundtrip() -> None:
    """Test Google Cloud KMS provider envelope encryption driver."""
    provider = GCPKMSSecretProvider(key_name="projects/test/cryptoKeys/kek")
    assert provider.provider_name == "gcp_kms"

    test_dek = b"abcdefghijabcdefghijabcdefghij12"  # 32 bytes
    enc_hex, version = await provider.encrypt_dek(
        test_dek, "projects/test/cryptoKeys/kek"
    )
    dec_dek = await provider.decrypt_dek(enc_hex, "projects/test/cryptoKeys/kek")
    assert dec_dek == test_dek

    health = await provider.health_check("projects/test/cryptoKeys/kek")
    assert health["status"] == "healthy"


@pytest.mark.anyio
async def test_vault_provider_roundtrip_fallback() -> None:
    """Test HashiCorp Vault provider with local dev emulation fallback."""
    provider = VaultSecretProvider(vault_addr="http://127.0.0.1:8200", vault_token="")
    assert provider.provider_name == "vault"

    test_dek = b"99999999998888888888777777777712"
    enc_hex, version = await provider.encrypt_dek(test_dek, "transit-kek")
    dec_dek = await provider.decrypt_dek(enc_hex, "transit-kek")
    assert dec_dek == test_dek

    health = await provider.health_check("transit-kek")
    assert health["status"] == "healthy"


# ── Secret Vault Service Lifecycle Tests ───────────────────────────────


@pytest.mark.anyio
async def test_store_secret_success(mock_session: AsyncMock) -> None:
    """Test storing an envelope-encrypted secret in the vault."""
    org_id = uuid4()
    actor_id = uuid4()

    # Mock no existing secret
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_res

    service = SecretVaultService(mock_session)
    req = CreateSecretRequestDTO(
        secret_name="prod_jira_api_token",
        secret_type=SecretType.INTEGRATION_TOKEN,
        plaintext_value="vn_jira_pat_token_secret_12345678",
        rotation_interval_days=90,
    )

    resp = await service.store_secret(
        req, organization_id=org_id, actor_user_id=actor_id
    )

    assert resp.secret_name == "prod_jira_api_token"
    assert resp.secret_type == SecretType.INTEGRATION_TOKEN
    assert resp.masked_value.endswith("5678")
    assert "vn_jira_pat" not in resp.masked_value  # Never expose full secret
    assert resp.rotation_interval_days == 90
    assert resp.status == SecretStatus.ACTIVE
    assert mock_session.add.call_count >= 3  # entry, rotation_policy, access_policy


@pytest.mark.anyio
async def test_store_duplicate_secret_name_rejected(mock_session: AsyncMock) -> None:
    """Test that storing duplicate secret name in same org raises ValidationException."""
    org_id = uuid4()
    existing_entry = SecretVaultEntryModel(
        id=uuid4(),
        organization_id=org_id,
        secret_name="duplicate_secret",
    )
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = existing_entry
    mock_session.execute.return_value = mock_res

    service = SecretVaultService(mock_session)
    req = CreateSecretRequestDTO(
        secret_name="duplicate_secret",
        plaintext_value="some_secret_value",
    )

    with pytest.raises(ValidationException, match="already exists"):
        await service.store_secret(req, organization_id=org_id)


@pytest.mark.anyio
async def test_access_secret_plaintext_success(mock_session: AsyncMock) -> None:
    """Test authorized access and decryption of secret plaintext."""
    org_id = uuid4()
    secret_id = uuid4()
    plaintext = "raw_unmasked_secret_string_4567"
    kek_id = f"org_{org_id}_kek"

    envelope = await EnvelopeEncryptionService.encrypt(
        plaintext=plaintext,
        kek_id=kek_id,
        provider_name="local",
    )

    entry = SecretVaultEntryModel(
        id=secret_id,
        organization_id=org_id,
        secret_name="my_secret",
        secret_type="API_KEY",
        provider=envelope.provider_name,
        kek_id=envelope.kek_id,
        encrypted_dek_hex=envelope.encrypted_dek_hex,
        encrypted_payload_hex=envelope.encrypted_payload_hex,
        nonce_hex=envelope.nonce_hex,
        tag_hex=envelope.tag_hex,
        key_version=1,
        status="ACTIVE",
        metadata_json={"masked_value": "********4567"},
        expires_at=None,
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = entry
    mock_session.execute.return_value = mock_res

    service = SecretVaultService(mock_session)
    decrypted_dto = await service.access_secret_plaintext(
        secret_id=secret_id,
        organization_id=org_id,
        actor_user_id=uuid4(),
        client_ip="192.168.1.50",
    )

    assert decrypted_dto.plaintext_value == plaintext
    assert decrypted_dto.secret_name == "my_secret"
    assert decrypted_dto.key_version == 1


@pytest.mark.anyio
async def test_access_revoked_secret_rejected(mock_session: AsyncMock) -> None:
    """Test that accessing a revoked secret raises ValidationException."""
    org_id = uuid4()
    secret_id = uuid4()

    entry = SecretVaultEntryModel(
        id=secret_id,
        organization_id=org_id,
        secret_name="revoked_token",
        secret_type="GENERIC",
        status="REVOKED",
        metadata_json={},
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = entry
    mock_session.execute.return_value = mock_res

    service = SecretVaultService(mock_session)
    with pytest.raises(ValidationException, match="has been revoked"):
        await service.access_secret_plaintext(
            secret_id=secret_id, organization_id=org_id
        )


@pytest.mark.anyio
async def test_access_expired_secret_rejected(mock_session: AsyncMock) -> None:
    """Test that accessing an expired secret marks it expired and raises ValidationException."""
    org_id = uuid4()
    secret_id = uuid4()
    expired_time = datetime.now(timezone.utc) - timedelta(days=2)

    entry = SecretVaultEntryModel(
        id=secret_id,
        organization_id=org_id,
        secret_name="expired_token",
        secret_type="GENERIC",
        status="ACTIVE",
        metadata_json={},
        expires_at=expired_time,
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = entry
    mock_session.execute.return_value = mock_res

    service = SecretVaultService(mock_session)
    with pytest.raises(ValidationException, match="has expired"):
        await service.access_secret_plaintext(
            secret_id=secret_id, organization_id=org_id
        )


@pytest.mark.anyio
async def test_revoke_secret_success(mock_session: AsyncMock) -> None:
    """Test revoking a secret."""
    org_id = uuid4()
    secret_id = uuid4()

    entry = SecretVaultEntryModel(
        id=secret_id,
        organization_id=org_id,
        secret_name="compromised_token",
        secret_type="API_KEY",
        provider="local",
        status="ACTIVE",
        key_version=1,
        metadata_json={},
    )
    policy = SecretRotationPolicyModel(
        id=uuid4(),
        organization_id=org_id,
        secret_id=secret_id,
        status="ACTIVE",
        rotation_interval_days=90,
        next_rotation_due=datetime.now(timezone.utc) + timedelta(days=90),
    )

    mock_res = MagicMock()
    mock_res.first.return_value = (entry, policy)
    mock_session.execute.return_value = mock_res

    service = SecretVaultService(mock_session)
    res = await service.revoke_secret(
        secret_id=secret_id,
        organization_id=org_id,
        reason="Compromised during security incident",
    )

    assert res.status == SecretStatus.REVOKED
    assert entry.status == "REVOKED"
    assert policy.status == "PAUSED"


@pytest.mark.anyio
async def test_delete_secret_success(mock_session: AsyncMock) -> None:
    """Test deleting a secret from the vault."""
    org_id = uuid4()
    secret_id = uuid4()

    entry = SecretVaultEntryModel(
        id=secret_id,
        organization_id=org_id,
        secret_name="old_key",
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = entry
    mock_session.execute.return_value = mock_res

    service = SecretVaultService(mock_session)
    res = await service.delete_secret(secret_id=secret_id, organization_id=org_id)

    assert res is True
    mock_session.delete.assert_called_once_with(entry)


# ── Secret Rotation Service Tests ──────────────────────────────────────


@pytest.mark.anyio
async def test_manual_rotate_secret(mock_session: AsyncMock) -> None:
    """Test manual rotation re-encrypting secret with fresh DEK and incrementing version."""
    org_id = uuid4()
    secret_id = uuid4()
    initial_plain = "secret_value_version_1"
    kek_id = f"org_{org_id}_kek"

    envelope = await EnvelopeEncryptionService.encrypt(initial_plain, kek_id, "local")

    entry = SecretVaultEntryModel(
        id=secret_id,
        organization_id=org_id,
        secret_name="rotating_secret",
        secret_type="INTEGRATION_TOKEN",
        provider="local",
        kek_id=kek_id,
        encrypted_dek_hex=envelope.encrypted_dek_hex,
        encrypted_payload_hex=envelope.encrypted_payload_hex,
        nonce_hex=envelope.nonce_hex,
        tag_hex=envelope.tag_hex,
        key_version=1,
        status="ACTIVE",
        metadata_json={"masked_value": "********on_1"},
    )
    policy = SecretRotationPolicyModel(
        id=uuid4(),
        organization_id=org_id,
        secret_id=secret_id,
        rotation_interval_days=90,
        next_rotation_due=datetime.now(timezone.utc) + timedelta(days=90),
        status="ACTIVE",
    )

    mock_res = MagicMock()
    mock_res.first.return_value = (entry, policy)
    mock_session.execute.return_value = mock_res

    service = SecretRotationService(mock_session)
    res = await service.rotate_secret(
        secret_id=secret_id,
        organization_id=org_id,
        new_plaintext_value="secret_value_version_2",
        reason="Manual credential rotation",
    )

    assert res.key_version == 2
    assert entry.key_version == 2
    assert res.masked_value.endswith("on_2")
    assert entry.last_rotated_at is not None


@pytest.mark.anyio
async def test_automated_rotation_worker(mock_session: AsyncMock) -> None:
    """Test background automated rotation worker processing expired secrets."""
    org_id = uuid4()
    secret_id = uuid4()
    kek_id = f"org_{org_id}_kek"

    envelope = await EnvelopeEncryptionService.encrypt(
        "auto_rotate_secret", kek_id, "local"
    )

    entry = SecretVaultEntryModel(
        id=secret_id,
        organization_id=org_id,
        secret_name="auto_rotating_key",
        secret_type="GENERIC",
        provider="local",
        kek_id=kek_id,
        encrypted_dek_hex=envelope.encrypted_dek_hex,
        encrypted_payload_hex=envelope.encrypted_payload_hex,
        nonce_hex=envelope.nonce_hex,
        tag_hex=envelope.tag_hex,
        key_version=1,
        status="ACTIVE",
        metadata_json={},
    )
    policy = SecretRotationPolicyModel(
        id=uuid4(),
        organization_id=org_id,
        secret_id=secret_id,
        rotation_interval_days=90,
        next_rotation_due=datetime.now(timezone.utc) - timedelta(days=1),  # Overdue
        status="ACTIVE",
    )

    # 1st call for scan, 2nd call for rotate lookup
    scan_res = MagicMock()
    scan_res.all.return_value = [(entry, policy)]

    rotate_res = MagicMock()
    rotate_res.first.return_value = (entry, policy)

    mock_session.execute.side_effect = [scan_res, rotate_res]

    service = SecretRotationService(mock_session)
    result = await service.check_and_rotate_expired_secrets(organization_id=org_id)

    assert result["rotated_count"] == 1
    assert result["failed_count"] == 0
    assert result["details"][0]["status"] == "ROTATED"


@pytest.mark.anyio
async def test_get_rotation_posture(mock_session: AsyncMock) -> None:
    """Test calculation of rotation compliance and upcoming expiration metrics."""
    org_id = uuid4()
    now = datetime.now(timezone.utc)

    # Mock total count
    count_res = MagicMock()
    count_res.scalar_one.return_value = 5

    # Mock active policies
    p1 = SecretRotationPolicyModel(
        id=uuid4(), next_rotation_due=now + timedelta(days=3)
    )  # Due in 7 days
    p2 = SecretRotationPolicyModel(
        id=uuid4(), next_rotation_due=now + timedelta(days=15)
    )  # Due in 30 days
    p3 = SecretRotationPolicyModel(
        id=uuid4(), next_rotation_due=now - timedelta(days=2)
    )  # Overdue
    p4 = SecretRotationPolicyModel(
        id=uuid4(), next_rotation_due=now + timedelta(days=60)
    )  # Not due soon

    policies_res = MagicMock()
    policies_res.scalars.return_value.all.return_value = [p1, p2, p3, p4]

    mock_session.execute.side_effect = [count_res, policies_res]

    service = SecretRotationService(mock_session)
    posture = await service.get_rotation_posture(organization_id=org_id)

    assert posture.total_secrets == 5
    assert posture.active_rotations == 4
    assert posture.due_in_7_days == 1
    assert posture.due_in_30_days == 2  # p1 + p2
    assert posture.overdue_rotations == 1  # p3


# ── KMS Health Service Tests ───────────────────────────────────────────


@pytest.mark.anyio
async def test_kms_health_service_all_providers() -> None:
    """Test probing health across all KMS providers."""
    health_results = await KMSHealthService.check_all_providers()
    assert len(health_results) >= 4
    providers = [h.provider for h in health_results]
    assert "local" in providers
    assert "vault" in providers
    assert "aws_kms" in providers
    assert "gcp_kms" in providers

    local_health = next(h for h in health_results if h.provider == "local")
    assert local_health.is_healthy is True


@pytest.mark.anyio
async def test_kms_health_service_active_provider() -> None:
    """Test probing health of active configured KMS provider."""
    active_health = await KMSHealthService.check_active_provider()
    assert active_health.provider is not None
    assert active_health.is_healthy is True
