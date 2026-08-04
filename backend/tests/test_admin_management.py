"""Unit and Integration Tests for Enterprise Administration & Governance Router."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.dependencies.api_key import get_current_user_or_api_key
from app.api.v1.dependencies.auth import get_current_active_user, get_current_user
from app.api.v1.dependencies.rbac import require_permission
from app.application.admin.admin_service import AdminService
from app.application.admin.dto import (
    APIKeyAdminItemDTO,
    APIKeyAdminListResponse,
    CreateAPIKeyAdminResponse,
    OrganizationAdminResponse,
    RolePermissionMatrixResponse,
    SecurityOverviewAdminResponse,
    UserAdminItemDTO,
    UserAdminListResponse,
)
from app.core.exceptions import ForbiddenException, ValidationException
from app.infrastructure.database.models.user import UserModel
from app.main import app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def mock_owner_user() -> UserModel:
    user = MagicMock(spec=UserModel)
    user.id = uuid4()
    user.organization_id = uuid4()
    user.email = "owner@enterprise.com"
    user.full_name = "Enterprise Owner"
    user.role = "OWNER"
    user.is_active = True
    return user


@pytest.fixture
def mock_admin_user(mock_owner_user: UserModel) -> UserModel:
    user = MagicMock(spec=UserModel)
    user.id = uuid4()
    user.organization_id = mock_owner_user.organization_id
    user.email = "admin@enterprise.com"
    user.full_name = "Admin User"
    user.role = "ADMIN"
    user.is_active = True
    return user


@pytest.mark.anyio
async def test_get_organization_details_service():
    """Test AdminService.get_organization_details retrieval."""
    mock_session = AsyncMock()
    service = AdminService(mock_session)

    org_id = uuid4()
    mock_org_dto = MagicMock()
    mock_org_dto.id = org_id
    mock_org_dto.name = "Acme Security Corp"
    mock_org_dto.slug = "acme-corp"
    mock_org_dto.plan_tier = "ENTERPRISE"
    mock_org_dto.is_active = True
    mock_org_dto.member_count = 5
    mock_org_dto.created_at = MagicMock()
    mock_org_dto.created_at.isoformat.return_value = "2026-08-01T00:00:00Z"
    mock_org_dto.updated_at = MagicMock()
    mock_org_dto.updated_at.isoformat.return_value = "2026-08-01T00:00:00Z"

    service.org_service.get_organization = AsyncMock(return_value=mock_org_dto)
    service.api_key_repo.list_by_organization = AsyncMock(return_value=[])

    result = await service.get_organization_details(org_id)

    assert isinstance(result, OrganizationAdminResponse)
    assert result.name == "Acme Security Corp"
    assert result.member_count == 5
    assert result.plan_tier == "ENTERPRISE"


@pytest.mark.anyio
async def test_deactivate_self_prevention(mock_admin_user: UserModel):
    """Test AdminService.deactivate_user prevents self-deactivation."""
    mock_session = AsyncMock()
    service = AdminService(mock_session)

    with pytest.raises(ForbiddenException):
        await service.deactivate_user(
            mock_admin_user.organization_id,
            mock_admin_user.id,
            mock_admin_user,
        )


@pytest.mark.anyio
async def test_sole_owner_demotion_prevention(mock_owner_user: UserModel):
    """Test AdminService.update_user_role prevents demoting sole owner."""
    mock_session = AsyncMock()
    service = AdminService(mock_session)

    service.user_repo.get_by_id_and_org = AsyncMock(return_value=mock_owner_user)
    service.user_repo.list_by_organization = AsyncMock(return_value=[mock_owner_user])

    mock_req = MagicMock()
    mock_req.role = "SECURITY_ANALYST"

    with pytest.raises(ValidationException):
        await service.update_user_role(
            mock_owner_user.organization_id,
            mock_owner_user.id,
            mock_req,
            mock_owner_user,
        )


@pytest.mark.anyio
async def test_role_permission_matrix_generation():
    """Test get_role_permission_matrix returns boundaries for all 4 roles."""
    mock_session = AsyncMock()
    service = AdminService(mock_session)

    result = await service.get_role_permission_matrix()

    assert isinstance(result, RolePermissionMatrixResponse)
    assert len(result.roles) == 4
    role_names = [r.role_name for r in result.roles]
    assert "OWNER" in role_names
    assert "ADMIN" in role_names
    assert "SECURITY_ANALYST" in role_names
    assert "VIEWER" in role_names


@pytest.mark.anyio
async def test_create_and_revoke_api_key_audit(mock_admin_user: UserModel):
    """Test API key generation and revocation trigger audit log events."""
    mock_session = AsyncMock()
    service = AdminService(mock_session)
    service.audit_service.record_event = AsyncMock()

    key_id = uuid4()
    mock_key_dto = MagicMock()
    mock_key_dto.id = key_id
    mock_key_dto.name = "CI Key"
    mock_key_dto.raw_key = "vn_live_abc123secret"

    mock_key_dto.key_prefix = "vn_live_"
    mock_key_dto.scopes = ["scans:read"]
    mock_key_dto.created_at = MagicMock()
    mock_key_dto.created_at.isoformat.return_value = "2026-08-01T00:00:00Z"
    mock_key_dto.expires_at = None

    service.api_key_service.create_api_key = AsyncMock(return_value=mock_key_dto)
    service.api_key_service.revoke_api_key = AsyncMock(return_value=True)

    mock_req = MagicMock()
    mock_req.name = "CI Key"
    mock_req.scopes = ["scans:read"]
    mock_req.expires_in_days = None

    created = await service.create_api_key(
        mock_admin_user.organization_id, mock_req, mock_admin_user
    )

    assert created.raw_api_key == "vn_live_abc123secret"
    service.audit_service.record_event.assert_called_with(
        organization_id=mock_admin_user.organization_id,
        action="api_key.created",
        resource_type="api_key",
        resource_id=str(key_id),
        actor_user_id=mock_admin_user.id,
        details={
            "name": "CI Key",
            "key_prefix": "vn_live_",
            "scopes": ["scans:read"],
            "expires_at": None,
        },
    )

    revoked = await service.revoke_api_key(
        mock_admin_user.organization_id, key_id, mock_admin_user
    )
    assert revoked is True
    service.audit_service.record_event.assert_called_with(
        organization_id=mock_admin_user.organization_id,
        action="api_key.revoked",
        resource_type="api_key",
        resource_id=str(key_id),
        actor_user_id=mock_admin_user.id,
        details={"api_key_id": str(key_id)},
    )


@pytest.mark.anyio
async def test_admin_rest_api_endpoints(mock_admin_user: UserModel):
    """Test REST API endpoint GET /api/v1/admin/organization."""
    org_id = mock_admin_user.organization_id
    mock_response = OrganizationAdminResponse(
        id=str(org_id),
        name="Acme Security Corp",
        slug="acme-corp",
        plan_tier="ENTERPRISE",
        is_active=True,
        member_count=3,
        total_scans_count=12,
        total_findings_count=4,
        active_api_keys_count=2,
        created_at="2026-08-01T00:00:00Z",
        updated_at="2026-08-01T00:00:00Z",
    )

    async def override_user():
        return mock_admin_user

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_current_active_user] = override_user
    app.dependency_overrides[get_current_user_or_api_key] = override_user

    with patch.object(
        AdminService,
        "get_organization_details",
        new=AsyncMock(return_value=mock_response),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get(
                "/api/v1/admin/organization",
                headers={"Authorization": "Bearer mocktoken"},
            )

    app.dependency_overrides.clear()

    assert res.status_code == 200
    res_data = res.json()
    assert res_data["name"] == "Acme Security Corp"
    assert res_data["plan_tier"] == "ENTERPRISE"
