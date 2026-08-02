"""Test Suite for Multi-Tenant RBAC Security Layer & Tenant Isolation."""

import asyncio
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI, status
from fastapi.testclient import TestClient

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.dependencies.rbac import (
    require_permission,
    require_role,
    require_same_organization,
    verify_organization_access,
)
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.domain.entities.role import (
    ALL_PERMISSIONS,
    PERMISSION_MAP,
    Role,
    parse_role,
    role_has_permission,
    role_meets_minimum,
)
from app.infrastructure.database.models.organization import OrganizationModel
from app.infrastructure.database.models.user import UserModel
from app.security.rbac import _resolve_user_role

# ───────────────────────────────────────────────
# 1. Domain Unit Tests: Role & Permission Model
# ───────────────────────────────────────────────


def test_role_hierarchy_ordering() -> None:
    """Verify Role enum ordering enforces OWNER > ADMIN > SECURITY_ANALYST > VIEWER."""
    assert Role.OWNER > Role.ADMIN
    assert Role.ADMIN > Role.SECURITY_ANALYST
    assert Role.SECURITY_ANALYST > Role.VIEWER

    assert Role.VIEWER < Role.SECURITY_ANALYST
    assert Role.SECURITY_ANALYST < Role.ADMIN
    assert Role.ADMIN < Role.OWNER


def test_parse_role_valid() -> None:
    """Verify parsing valid role strings regardless of casing or whitespace."""
    assert parse_role("VIEWER") == Role.VIEWER
    assert parse_role("security_analyst") == Role.SECURITY_ANALYST
    assert parse_role("  Admin  ") == Role.ADMIN
    assert parse_role("owner") == Role.OWNER


def test_parse_role_invalid() -> None:
    """Verify parsing invalid role string raises ValueError."""
    with pytest.raises(ValueError, match="Unknown role 'SUPER_USER'"):
        parse_role("SUPER_USER")


def test_role_meets_minimum() -> None:
    """Verify role_meets_minimum comparison across all levels."""
    assert role_meets_minimum(Role.OWNER, Role.ADMIN) is True
    assert role_meets_minimum(Role.ADMIN, Role.ADMIN) is True
    assert role_meets_minimum(Role.SECURITY_ANALYST, Role.ADMIN) is False
    assert role_meets_minimum(Role.VIEWER, Role.SECURITY_ANALYST) is False


def test_permission_map_completeness() -> None:
    """Verify PERMISSION_MAP contains non-empty permissions mapped to Role instances."""
    assert len(PERMISSION_MAP) > 0
    assert ALL_PERMISSIONS == set(PERMISSION_MAP.keys())
    for perm, role in PERMISSION_MAP.items():
        assert isinstance(perm, str)
        assert isinstance(role, Role)


def test_role_has_permission_hierarchical_inheritance() -> None:
    """Verify higher roles inherit permissions of lower roles."""
    # Organization deletion requires OWNER
    assert role_has_permission(Role.OWNER, "organization:delete") is True
    assert role_has_permission(Role.ADMIN, "organization:delete") is False
    assert role_has_permission(Role.SECURITY_ANALYST, "organization:delete") is False
    assert role_has_permission(Role.VIEWER, "organization:delete") is False

    # Scan creation requires SECURITY_ANALYST
    assert role_has_permission(Role.OWNER, "scans:create") is True
    assert role_has_permission(Role.ADMIN, "scans:create") is True
    assert role_has_permission(Role.SECURITY_ANALYST, "scans:create") is True
    assert role_has_permission(Role.VIEWER, "scans:create") is False

    # Scan reading requires VIEWER
    assert role_has_permission(Role.OWNER, "scans:read") is True
    assert role_has_permission(Role.ADMIN, "scans:read") is True
    assert role_has_permission(Role.SECURITY_ANALYST, "scans:read") is True
    assert role_has_permission(Role.VIEWER, "scans:read") is True


def test_role_has_permission_unknown_permission_denied() -> None:
    """Verify unknown permissions fail closed (return False)."""
    assert role_has_permission(Role.OWNER, "unknown:permission") is False


# ───────────────────────────────────────────────
# 2. Security Module Unit Tests: RBAC Helpers
# ───────────────────────────────────────────────


def test_resolve_user_role_safe_fallback() -> None:
    """Verify _resolve_user_role defaults to VIEWER for unrecognized role string."""
    mock_user = MagicMock(spec=UserModel)
    mock_user.role = "UNKNOWN_CORRUPTED_ROLE"

    resolved_role = _resolve_user_role(mock_user)
    assert resolved_role == Role.VIEWER


def test_verify_organization_access_success_and_failure() -> None:
    """Verify tenant isolation helper matches organization_id or raises ForbiddenException."""
    org_id_a = uuid4()
    org_id_b = uuid4()

    mock_user = MagicMock(spec=UserModel)
    mock_user.organization_id = org_id_a

    # Matching org -> No exception
    verify_organization_access(mock_user, org_id_a)

    # Different org -> ForbiddenException (403)
    with pytest.raises(
        ForbiddenException, match="belongs to a different organization"
    ) as exc_info:
        verify_organization_access(mock_user, org_id_b)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.code == "FORBIDDEN"


# ───────────────────────────────────────────────
# 3. Integration & Endpoint Authorization Tests
# ───────────────────────────────────────────────

from app.core.exceptions import VulnovaException
from app.main import vulnova_exception_handler

# Set up test router with RBAC dependencies and Vulnova exception handling
rbac_test_app = FastAPI()
rbac_test_app.add_exception_handler(VulnovaException, vulnova_exception_handler)

org_a_id = uuid4()
org_b_id = uuid4()


@rbac_test_app.get(
    "/test/viewer-permission",
    dependencies=[Depends(require_permission("scans:read"))],
)
async def viewer_permission_endpoint() -> dict:
    return {"message": "viewer access granted"}


@rbac_test_app.post(
    "/test/analyst-permission",
    dependencies=[Depends(require_permission("scans:create"))],
)
async def analyst_permission_endpoint() -> dict:
    return {"message": "analyst access granted"}


@rbac_test_app.delete(
    "/test/owner-permission",
    dependencies=[Depends(require_permission("organization:delete"))],
)
async def owner_permission_endpoint() -> dict:
    return {"message": "owner access granted"}


@rbac_test_app.get(
    "/test/admin-role",
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def admin_role_endpoint() -> dict:
    return {"message": "admin role granted"}


@rbac_test_app.get("/test/tenant/{target_org_id}")
async def tenant_isolation_endpoint(
    target_org_id: str,
    user: UserModel = Depends(get_current_user),
) -> dict:
    from uuid import UUID

    verify_organization_access(user, UUID(target_org_id))
    return {"message": "tenant access granted", "org_id": str(user.organization_id)}


def _make_mock_user(role_name: str, org_id=org_a_id) -> UserModel:
    user = MagicMock(spec=UserModel)
    user.id = uuid4()
    user.organization_id = org_id
    user.role = role_name
    user.is_active = True
    user.email = f"{role_name.lower()}@acme.com"
    return user


def test_api_rbac_viewer_permissions() -> None:
    """Test VIEWER role can access viewer endpoints but is denied analyst/owner actions."""
    viewer_user = _make_mock_user("VIEWER")
    rbac_test_app.dependency_overrides[get_current_user] = lambda: viewer_user

    client = TestClient(rbac_test_app)
    try:
        # Viewer endpoint -> 200 OK
        res = client.get("/test/viewer-permission")
        assert res.status_code == 200
        assert res.json()["message"] == "viewer access granted"

        # Analyst endpoint -> 403 Forbidden
        res = client.post("/test/analyst-permission")
        assert res.status_code == 403
        assert res.json()["error"]["code"] == "FORBIDDEN"

        # Owner endpoint -> 403 Forbidden
        res = client.delete("/test/owner-permission")
        assert res.status_code == 403
        assert res.json()["error"]["code"] == "FORBIDDEN"

        # Admin role endpoint -> 403 Forbidden
        res = client.get("/test/admin-role")
        assert res.status_code == 403
        assert res.json()["error"]["code"] == "FORBIDDEN"
    finally:
        rbac_test_app.dependency_overrides.clear()


def test_api_rbac_security_analyst_permissions() -> None:
    """Test SECURITY_ANALYST role can access analyst endpoints but is denied owner actions."""
    analyst_user = _make_mock_user("SECURITY_ANALYST")
    rbac_test_app.dependency_overrides[get_current_user] = lambda: analyst_user

    client = TestClient(rbac_test_app)
    try:
        # Viewer endpoint -> 200 OK
        res = client.get("/test/viewer-permission")
        assert res.status_code == 200

        # Analyst endpoint -> 200 OK
        res = client.post("/test/analyst-permission")
        assert res.status_code == 200

        # Owner endpoint -> 403 Forbidden
        res = client.delete("/test/owner-permission")
        assert res.status_code == 403

        # Admin role endpoint -> 403 Forbidden
        res = client.get("/test/admin-role")
        assert res.status_code == 403
    finally:
        rbac_test_app.dependency_overrides.clear()


def test_api_rbac_owner_permissions() -> None:
    """Test OWNER role can access all endpoints (viewer, analyst, admin, owner)."""
    owner_user = _make_mock_user("OWNER")
    rbac_test_app.dependency_overrides[get_current_user] = lambda: owner_user

    client = TestClient(rbac_test_app)
    try:
        assert client.get("/test/viewer-permission").status_code == 200
        assert client.post("/test/analyst-permission").status_code == 200
        assert client.delete("/test/owner-permission").status_code == 200
        assert client.get("/test/admin-role").status_code == 200
    finally:
        rbac_test_app.dependency_overrides.clear()


def test_api_rbac_invalid_role_fails_safely() -> None:
    """Test user with invalid/unrecognized role string fails safely to VIEWER (denied analyst endpoint)."""
    corrupt_user = _make_mock_user("MALICIOUS_CUSTOM_ROLE")
    rbac_test_app.dependency_overrides[get_current_user] = lambda: corrupt_user

    client = TestClient(rbac_test_app)
    try:
        # Analyst endpoint denied -> 403 Forbidden
        res = client.post("/test/analyst-permission")
        assert res.status_code == 403

        # Viewer endpoint allowed -> 200 OK
        res = client.get("/test/viewer-permission")
        assert res.status_code == 200
    finally:
        rbac_test_app.dependency_overrides.clear()


def test_api_rbac_unauthenticated_denied() -> None:
    """Test missing authentication credentials raises 401 Unauthorized."""

    def _unauthorized_override():
        raise UnauthorizedException("Authentication token required")

    rbac_test_app.dependency_overrides[get_current_user] = _unauthorized_override

    client = TestClient(rbac_test_app)
    try:
        res = client.get("/test/viewer-permission")
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "UNAUTHORIZED"
    finally:
        rbac_test_app.dependency_overrides.clear()


def test_api_tenant_isolation_enforced() -> None:
    """Test cross-tenant resource access raises 403 Forbidden."""
    user_org_a = _make_mock_user("SECURITY_ANALYST", org_id=org_a_id)
    rbac_test_app.dependency_overrides[get_current_user] = lambda: user_org_a

    client = TestClient(rbac_test_app)
    try:
        # Requesting own tenant resource -> 200 OK
        res = client.get(f"/test/tenant/{org_a_id}")
        assert res.status_code == 200
        assert res.json()["org_id"] == str(org_a_id)

        # Requesting different tenant resource -> 403 Forbidden
        res = client.get(f"/test/tenant/{org_b_id}")
        assert res.status_code == 403
        assert res.json()["error"]["code"] == "FORBIDDEN"
        assert "different organization" in res.json()["error"]["message"]
    finally:
        rbac_test_app.dependency_overrides.clear()
