"""Phase 2.1 — SQLAlchemy ORM Models & Alembic Revisions Test Suite."""

from alembic.script import ScriptDirectory
from alembic.config import Config
from app.infrastructure.database.base import Base
from app.infrastructure.database.models import (
    APIKeyModel,
    AuditLogModel,
    OrganizationModel,
    RefreshTokenModel,
    UserModel,
)


def test_orm_models_registered_in_base_metadata() -> None:
    """Verify all Core Platform ORM models register their tables in Base.metadata."""
    tables = Base.metadata.tables.keys()
    assert "organizations" in tables
    assert "users" in tables
    assert "refresh_tokens" in tables
    assert "api_keys" in tables
    assert "audit_logs" in tables


def test_organization_model_table_structure() -> None:
    """Verify OrganizationModel columns and tablename."""
    assert OrganizationModel.__tablename__ == "organizations"
    table = OrganizationModel.__table__
    assert "id" in table.columns
    assert "name" in table.columns
    assert "slug" in table.columns
    assert "plan_tier" in table.columns
    assert "is_active" in table.columns
    assert table.columns["slug"].unique is True


def test_user_model_table_structure() -> None:
    """Verify UserModel columns and foreign key to organizations."""
    assert UserModel.__tablename__ == "users"
    table = UserModel.__table__
    assert "id" in table.columns
    assert "organization_id" in table.columns
    assert "email" in table.columns
    assert "password_hash" in table.columns
    assert table.columns["email"].unique is True


def test_refresh_token_model_table_structure() -> None:
    """Verify RefreshTokenModel columns and foreign key to users."""
    assert RefreshTokenModel.__tablename__ == "refresh_tokens"
    table = RefreshTokenModel.__table__
    assert "id" in table.columns
    assert "user_id" in table.columns
    assert "family_id" in table.columns
    assert "token_hash" in table.columns
    assert "is_revoked" in table.columns


def test_api_key_model_table_structure() -> None:
    """Verify APIKeyModel columns and foreign keys."""
    assert APIKeyModel.__tablename__ == "api_keys"
    table = APIKeyModel.__table__
    assert "id" in table.columns
    assert "organization_id" in table.columns
    assert "user_id" in table.columns
    assert "key_prefix" in table.columns
    assert "key_hash" in table.columns


def test_audit_log_model_table_structure() -> None:
    """Verify AuditLogModel columns and relationships."""
    assert AuditLogModel.__tablename__ == "audit_logs"
    table = AuditLogModel.__table__
    assert "id" in table.columns
    assert "organization_id" in table.columns
    assert "actor_user_id" in table.columns
    assert "action" in table.columns
    assert "resource_type" in table.columns


def test_alembic_revision_chain() -> None:
    """Verify Alembic script directory has a valid single revision head."""
    alembic_cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)
    heads = script.get_heads()
    assert len(heads) == 1
    assert heads[0] == script.get_current_head()
