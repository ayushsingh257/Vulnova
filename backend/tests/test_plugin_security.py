"""Unit and Integration Tests for Phase 12.7 Cryptographically Signed & Sandboxed Plugin Ecosystem Architecture."""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric import ed25519
import pytest

from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.infrastructure.database.models.plugin_security import (
    PluginExecutionAuditModel,
    PluginManifestModel,
    PluginSignatureModel,
    PluginTrustedPublisherModel,
)
from app.infrastructure.plugin_security.capability_service import (
    PluginCapabilityService,
)
from app.infrastructure.plugin_security.dto import (
    PluginCapability,
    PluginExecutionRequestDTO,
    PluginManifestDTO,
    PluginVerificationStatus,
    PublisherTrustStatus,
    RegisterPublisherRequestDTO,
)
from app.infrastructure.plugin_security.runner_service import (
    PluginRunnerService,
)
from app.infrastructure.plugin_security.security_report_service import (
    PluginSecurityReportService,
)
from app.infrastructure.plugin_security.signature_service import (
    PluginSignatureService,
)
from app.infrastructure.plugin_security.trust_service import (
    PluginTrustService,
)


@pytest.fixture
def mock_session() -> AsyncMock:
    """Provide a mock AsyncSession."""
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture
def sample_keypair() -> tuple[ed25519.Ed25519PrivateKey, str, str]:
    """Generate a sample Ed25519 private key, public key hex, and public key fingerprint."""
    priv = ed25519.Ed25519PrivateKey.generate()
    pub_hex = priv.public_key().public_bytes_raw().hex()
    fingerprint = PluginSignatureService.calculate_key_fingerprint(pub_hex)
    return priv, pub_hex, fingerprint


def _make_manifest(
    plugin_id: str = "web_xss_scanner",
    publisher_id: str = "vulnova-official",
    capabilities: list[PluginCapability] | None = None,
) -> PluginManifestDTO:
    """Helper to create a standard PluginManifestDTO."""
    caps = capabilities or [PluginCapability.NETWORK_HTTP, PluginCapability.NETWORK_DNS]
    return PluginManifestDTO(
        plugin_id=plugin_id,
        name="Web XSS Vulnerability Scanner",
        version="1.0.0",
        publisher_id=publisher_id,
        description="High-performance XSS detection plugin with sandbox boundaries",
        entrypoint="plugins.xss.scanner:XSSScanner",
        capabilities=caps,
        package_hash="a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
    )


@pytest.mark.anyio
async def test_key_generation_and_fingerprint(sample_keypair: Any) -> None:
    """Validate Ed25519 key generation and SHA-256 fingerprint generation."""
    _, pub_hex, fingerprint = sample_keypair
    assert len(pub_hex) == 64
    assert len(fingerprint) == 64
    assert PluginSignatureService.calculate_key_fingerprint(pub_hex) == fingerprint


@pytest.mark.anyio
async def test_valid_signed_plugin_accepted(
    mock_session: AsyncMock, sample_keypair: Any
) -> None:
    """Valid Ed25519 signature from trusted publisher is verified and accepted."""
    priv, pub_hex, fingerprint = sample_keypair
    org_id = uuid4()
    publisher_id = "vulnova-official"
    manifest = _make_manifest(publisher_id=publisher_id)

    # 1. Setup mock trusted publisher in database
    pub_model = PluginTrustedPublisherModel(
        id=uuid4(),
        organization_id=org_id,
        publisher_id=publisher_id,
        publisher_name="Vulnova Official Security Team",
        public_key_hex=pub_hex,
        public_key_fingerprint=fingerprint,
        trust_status="TRUSTED",
        created_at=datetime.now(timezone.utc),
    )

    async def _mock_exec(stmt: Any, *a: Any, **kw: Any) -> MagicMock:
        res = MagicMock()
        res.scalar_one_or_none.return_value = pub_model
        return res

    mock_session.execute.side_effect = _mock_exec

    # 2. Sign manifest with Ed25519 private key
    sig_hex = PluginSignatureService.sign_manifest(manifest, priv)

    # 3. Verify signature
    sig_svc = PluginSignatureService(mock_session)
    sig_svc.audit_service.record_event = AsyncMock()

    result = await sig_svc.verify_plugin_signature(manifest, sig_hex, org_id)

    assert result.is_valid is True
    assert result.verification_status == PluginVerificationStatus.VERIFIED
    assert result.trust_status == PublisherTrustStatus.TRUSTED
    assert result.public_key_fingerprint == fingerprint
    assert mock_session.add.called


@pytest.mark.anyio
async def test_unsigned_or_unknown_publisher_rejected(
    mock_session: AsyncMock,
) -> None:
    """Plugin from unknown or unregistered publisher is rejected with UNKNOWN_PUBLISHER."""
    org_id = uuid4()
    manifest = _make_manifest(publisher_id="rogue-author")

    async def _mock_exec(stmt: Any, *a: Any, **kw: Any) -> MagicMock:
        res = MagicMock()
        res.scalar_one_or_none.return_value = None
        return res

    mock_session.execute.side_effect = _mock_exec

    sig_svc = PluginSignatureService(mock_session)
    sig_svc.audit_service.record_event = AsyncMock()

    result = await sig_svc.verify_plugin_signature(manifest, "deadbeef" * 8, org_id)

    assert result.is_valid is False
    assert result.verification_status == PluginVerificationStatus.UNKNOWN_PUBLISHER
    assert result.trust_status == PublisherTrustStatus.UNTRUSTED


@pytest.mark.anyio
async def test_invalid_signature_rejected(
    mock_session: AsyncMock, sample_keypair: Any
) -> None:
    """Corrupted or mismatched signature is rejected with INVALID_SIGNATURE."""
    _, pub_hex, fingerprint = sample_keypair
    org_id = uuid4()
    publisher_id = "vulnova-official"
    manifest = _make_manifest(publisher_id=publisher_id)

    pub_model = PluginTrustedPublisherModel(
        id=uuid4(),
        organization_id=org_id,
        publisher_id=publisher_id,
        publisher_name="Vulnova Official",
        public_key_hex=pub_hex,
        public_key_fingerprint=fingerprint,
        trust_status="TRUSTED",
        created_at=datetime.now(timezone.utc),
    )

    async def _mock_exec(stmt: Any, *a: Any, **kw: Any) -> MagicMock:
        res = MagicMock()
        res.scalar_one_or_none.return_value = pub_model
        return res

    mock_session.execute.side_effect = _mock_exec

    sig_svc = PluginSignatureService(mock_session)
    sig_svc.audit_service.record_event = AsyncMock()

    # Pass invalid/tampered signature bytes
    result = await sig_svc.verify_plugin_signature(manifest, "00" * 64, org_id)

    assert result.is_valid is False
    assert result.verification_status == PluginVerificationStatus.INVALID_SIGNATURE


@pytest.mark.anyio
async def test_revoked_publisher_rejected(
    mock_session: AsyncMock, sample_keypair: Any
) -> None:
    """Plugins signed by revoked publishers are rejected with REVOKED_PUBLISHER."""
    priv, pub_hex, fingerprint = sample_keypair
    org_id = uuid4()
    publisher_id = "compromised-vendor"
    manifest = _make_manifest(publisher_id=publisher_id)

    pub_model = PluginTrustedPublisherModel(
        id=uuid4(),
        organization_id=org_id,
        publisher_id=publisher_id,
        publisher_name="Compromised Vendor",
        public_key_hex=pub_hex,
        public_key_fingerprint=fingerprint,
        trust_status="REVOKED",
        revocation_reason="Private key leaked in public repository",
        created_at=datetime.now(timezone.utc),
    )

    async def _mock_exec(stmt: Any, *a: Any, **kw: Any) -> MagicMock:
        res = MagicMock()
        res.scalar_one_or_none.return_value = pub_model
        return res

    mock_session.execute.side_effect = _mock_exec

    sig_hex = PluginSignatureService.sign_manifest(manifest, priv)
    sig_svc = PluginSignatureService(mock_session)
    sig_svc.audit_service.record_event = AsyncMock()

    result = await sig_svc.verify_plugin_signature(manifest, sig_hex, org_id)

    assert result.is_valid is False
    assert result.verification_status == PluginVerificationStatus.REVOKED_PUBLISHER
    assert result.trust_status == PublisherTrustStatus.REVOKED


@pytest.mark.anyio
async def test_publisher_trust_registration_and_revocation(
    mock_session: AsyncMock, sample_keypair: Any
) -> None:
    """Register publisher, verify trust status, and revoke trust."""
    _, pub_hex, _ = sample_keypair
    org_id = uuid4()

    trust_svc = PluginTrustService(mock_session)
    trust_svc.audit_service.record_event = AsyncMock()

    async def _mock_exec(stmt: Any, *a: Any, **kw: Any) -> MagicMock:
        res = MagicMock()
        res.scalar_one_or_none.return_value = None
        return res

    mock_session.execute.side_effect = _mock_exec

    # 1. Register publisher
    req = RegisterPublisherRequestDTO(
        publisher_id="partner-sec",
        publisher_name="Partner Security Labs",
        public_key_hex=pub_hex,
        contact_email="security@partner.com",
    )
    pub = await trust_svc.register_trusted_publisher(req, org_id)
    assert pub.publisher_id == "partner-sec"
    assert pub.trust_status == PublisherTrustStatus.TRUSTED

    # 2. Revoke publisher
    pub_model = PluginTrustedPublisherModel(
        id=pub.id,
        organization_id=org_id,
        publisher_id="partner-sec",
        publisher_name="Partner Security Labs",
        public_key_hex=pub_hex,
        public_key_fingerprint=pub.public_key_fingerprint,
        trust_status="TRUSTED",
        created_at=datetime.now(timezone.utc),
    )

    async def _mock_exec_revoke(stmt: Any, *a: Any, **kw: Any) -> MagicMock:
        res = MagicMock()
        res.scalar_one_or_none.return_value = pub_model
        return res

    mock_session.execute.side_effect = _mock_exec_revoke

    revoked = await trust_svc.revoke_publisher(
        "partner-sec", org_id, reason="Partnership ended"
    )
    assert revoked.trust_status == PublisherTrustStatus.REVOKED
    assert revoked.revocation_reason == "Partnership ended"


@pytest.mark.anyio
async def test_capability_manifest_validation_and_enforcement(
    mock_session: AsyncMock,
) -> None:
    """Validate capability parsing and permission enforcement against undeclared capabilities."""
    cap_svc = PluginCapabilityService(mock_session)

    # 1. Parse valid manifest dict
    manifest_dict = {
        "name": "web_scanner",
        "version": "1.0.0",
        "publisher": "vulnova",
        "capabilities": ["network:http", "network:dns"],
        "package_hash": "abc123hash",
    }
    manifest = cap_svc.parse_and_validate_manifest(manifest_dict)
    assert manifest.plugin_id == "web_scanner"
    assert PluginCapability.NETWORK_HTTP in manifest.capabilities

    # 2. Permission enforcement: Undeclared capability throws ValidationException
    with pytest.raises(ValidationException, match="Permission Denied"):
        cap_svc.enforce_runtime_permissions(
            plugin_id="web_scanner",
            declared_capabilities=[PluginCapability.NETWORK_HTTP],
            required_capabilities=[
                PluginCapability.NETWORK_HTTP,
                PluginCapability.PROCESS_EXECUTE,
            ],
        )


@pytest.mark.anyio
async def test_plugin_runner_blocks_unverified_execution(
    mock_session: AsyncMock,
) -> None:
    """PluginRunner blocks execution of unsigned or unverified plugins."""
    org_id = uuid4()
    req = PluginExecutionRequestDTO(
        plugin_id="unverified_plugin",
        target_url="https://example.com",
    )

    async def _mock_exec(stmt: Any, *a: Any, **kw: Any) -> MagicMock:
        res = MagicMock()
        res.scalar_one_or_none.return_value = None
        return res

    mock_session.execute.side_effect = _mock_exec

    runner = PluginRunnerService(mock_session)
    runner.audit_service.record_event = AsyncMock()

    with pytest.raises(ValidationException, match="Execution Blocked"):
        await runner.execute_plugin(req, org_id)


@pytest.mark.anyio
async def test_plugin_runner_executes_verified_plugin(
    mock_session: AsyncMock, sample_keypair: Any
) -> None:
    """Verified plugin executes inside isolated sandbox and records audit logs."""
    _, pub_hex, fingerprint = sample_keypair
    org_id = uuid4()
    plugin_id = "signed_sql_scanner"

    sig_model = PluginSignatureModel(
        id=uuid4(),
        organization_id=org_id,
        plugin_id=plugin_id,
        publisher_id="vulnova-core",
        signature_hex="sig123",
        public_key_fingerprint=fingerprint,
        verification_status="VERIFIED",
        verified_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )

    pub_model = PluginTrustedPublisherModel(
        id=uuid4(),
        organization_id=org_id,
        publisher_id="vulnova-core",
        publisher_name="Vulnova Core",
        public_key_hex=pub_hex,
        public_key_fingerprint=fingerprint,
        trust_status="TRUSTED",
        created_at=datetime.now(timezone.utc),
    )

    man_model = PluginManifestModel(
        id=uuid4(),
        organization_id=org_id,
        plugin_id=plugin_id,
        name="SQL Injection Scanner",
        version="1.2.0",
        publisher_id="vulnova-core",
        capabilities_json=["network:http"],
        package_hash="hash123",
        created_at=datetime.now(timezone.utc),
    )

    async def _mock_exec(stmt: Any, *a: Any, **kw: Any) -> MagicMock:
        stmt_str = str(stmt).lower()
        res = MagicMock()
        if "plugin_signatures" in stmt_str:
            res.scalar_one_or_none.return_value = sig_model
        elif "plugin_trusted_publishers" in stmt_str:
            res.scalar_one_or_none.return_value = pub_model
        elif "plugin_manifests" in stmt_str:
            res.scalar_one_or_none.return_value = man_model
        else:
            res.scalar_one_or_none.return_value = None
        return res

    mock_session.execute.side_effect = _mock_exec

    runner = PluginRunnerService(mock_session)
    runner.audit_service.record_event = AsyncMock()

    req = PluginExecutionRequestDTO(
        plugin_id=plugin_id,
        target_url="https://example.com",
        timeout_seconds=10,
    )

    result = await runner.execute_plugin(req, org_id)

    assert result.status == "SUCCESS"
    assert result.findings_count >= 1
    assert result.sandbox_driver == "subprocess"
    assert mock_session.add.called


@pytest.mark.anyio
async def test_plugin_security_report_generation(
    mock_session: AsyncMock, sample_keypair: Any
) -> None:
    """Generate comprehensive zero-trust security report for a plugin."""
    _, pub_hex, fingerprint = sample_keypair
    org_id = uuid4()
    plugin_id = "web_xss_plugin"

    man_model = PluginManifestModel(
        id=uuid4(),
        organization_id=org_id,
        plugin_id=plugin_id,
        name="XSS Detector",
        version="1.0.0",
        publisher_id="vulnova-sec",
        capabilities_json=["network:http", "network:dns"],
        package_hash="hash456",
        created_at=datetime.now(timezone.utc),
    )

    pub_model = PluginTrustedPublisherModel(
        id=uuid4(),
        organization_id=org_id,
        publisher_id="vulnova-sec",
        publisher_name="Vulnova Security",
        public_key_hex=pub_hex,
        public_key_fingerprint=fingerprint,
        trust_status="TRUSTED",
        created_at=datetime.now(timezone.utc),
    )

    sig_model = PluginSignatureModel(
        id=uuid4(),
        organization_id=org_id,
        plugin_id=plugin_id,
        publisher_id="vulnova-sec",
        signature_hex="sig456",
        public_key_fingerprint=fingerprint,
        verification_status="VERIFIED",
        verified_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )

    async def _mock_exec(stmt: Any, *a: Any, **kw: Any) -> MagicMock:
        stmt_str = str(stmt).lower()
        res = MagicMock()
        if "plugin_manifests" in stmt_str:
            res.scalar_one_or_none.return_value = man_model
        elif "plugin_trusted_publishers" in stmt_str:
            res.scalar_one_or_none.return_value = pub_model
        elif "plugin_signatures" in stmt_str:
            res.scalar_one_or_none.return_value = sig_model
        elif "count" in stmt_str:
            res.scalar_one.return_value = 5
        else:
            res.scalar_one_or_none.return_value = None
        return res

    mock_session.execute.side_effect = _mock_exec

    report_svc = PluginSecurityReportService(mock_session)
    report = await report_svc.generate_security_report(plugin_id, org_id)

    assert report.plugin_id == plugin_id
    assert report.signature_valid is True
    assert report.trust_status == PublisherTrustStatus.TRUSTED
    assert PluginCapability.NETWORK_HTTP in report.capabilities
    assert report.sandbox_enforced is True
