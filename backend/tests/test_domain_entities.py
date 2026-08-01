"""Phase 2.1 — Domain Entities Test Suite."""

from datetime import datetime, timezone
from uuid import UUID

from app.domain.entities import (
    APIKey,
    AuditLog,
    Organization,
    RefreshToken,
    User,
)


def test_organization_entity_defaults() -> None:
    """Verify Organization domain entity creation with defaults."""
    org = Organization(name="Acme Corp", slug="acme-corp")
    assert isinstance(org.id, UUID)
    assert org.name == "Acme Corp"
    assert org.slug == "acme-corp"
    assert org.plan_tier == "ENTERPRISE_TRIAL"
    assert org.is_active is True
    assert isinstance(org.created_at, datetime)
    assert isinstance(org.updated_at, datetime)


def test_user_entity_defaults() -> None:
    """Verify User domain entity creation with defaults."""
    org = Organization(name="Acme Corp", slug="acme-corp")
    user = User(
        organization_id=org.id,
        email="admin@acme.com",
        password_hash="argon2_hashed_secret",
        full_name="Alice Admin",
    )
    assert isinstance(user.id, UUID)
    assert user.organization_id == org.id
    assert user.email == "admin@acme.com"
    assert user.role == "SECURITY_ANALYST"
    assert user.is_active is True
    assert user.is_mfa_enabled is False
    assert user.mfa_secret is None
    assert user.last_login_at is None


def test_refresh_token_entity_defaults() -> None:
    """Verify RefreshToken domain entity creation."""
    org = Organization(name="Acme Corp", slug="acme-corp")
    user = User(
        organization_id=org.id,
        email="user@acme.com",
        password_hash="hash",
        full_name="Bob",
    )
    exp = datetime.now(timezone.utc)
    from uuid import uuid4

    family_id = uuid4()

    token = RefreshToken(
        user_id=user.id,
        family_id=family_id,
        token_hash="sha256_hash_value",
        expires_at=exp,
    )
    assert isinstance(token.id, UUID)
    assert token.user_id == user.id
    assert token.family_id == family_id
    assert token.token_hash == "sha256_hash_value"
    assert token.is_revoked is False
    assert token.expires_at == exp


def test_api_key_entity_defaults() -> None:
    """Verify APIKey domain entity creation with defaults."""
    org = Organization(name="Acme Corp", slug="acme-corp")
    user = User(
        organization_id=org.id,
        email="user@acme.com",
        password_hash="hash",
        full_name="Bob",
    )
    api_key = APIKey(
        organization_id=org.id,
        user_id=user.id,
        name="CI/CD Integration Key",
        key_prefix="vn_live_",
        key_hash="sha256_key_hash",
    )
    assert isinstance(api_key.id, UUID)
    assert api_key.organization_id == org.id
    assert api_key.user_id == user.id
    assert api_key.scopes == ["read", "write"]
    assert api_key.expires_at is None
    assert api_key.last_used_at is None


def test_audit_log_entity_defaults() -> None:
    """Verify AuditLog domain entity creation."""
    org = Organization(name="Acme Corp", slug="acme-corp")
    user = User(
        organization_id=org.id,
        email="user@acme.com",
        password_hash="hash",
        full_name="Bob",
    )
    audit = AuditLog(
        organization_id=org.id,
        actor_user_id=user.id,
        action="user.login.success",
        resource_type="user",
        resource_id=str(user.id),
        client_ip="192.168.1.100",
        details={"browser": "Chrome"},
    )
    assert isinstance(audit.id, UUID)
    assert audit.organization_id == org.id
    assert audit.actor_user_id == user.id
    assert audit.action == "user.login.success"
    assert audit.details == {"browser": "Chrome"}
