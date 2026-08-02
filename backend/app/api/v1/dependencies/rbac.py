"""FastAPI RBAC & Tenant Isolation Dependencies Exporter."""

from app.security.rbac import (
    require_permission,
    require_role,
    require_same_organization,
    verify_organization_access,
)

__all__ = [
    "require_role",
    "require_permission",
    "require_same_organization",
    "verify_organization_access",
]
