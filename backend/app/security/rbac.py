"""Vulnova RBAC Authorization Dependencies.

FastAPI dependency factories for role-based access control and tenant isolation.
These dependencies run AFTER authentication (get_current_user) and enforce
authorization checks before endpoint handlers execute.
"""

from typing import Any, Callable
from uuid import UUID

from fastapi import Depends

from app.api.v1.dependencies.auth import get_current_user
from app.core.exceptions import ForbiddenException
from app.core.logging import get_logger
from app.domain.entities.role import (
    Role,
    parse_role,
    role_has_permission,
    role_meets_minimum,
)
from app.infrastructure.database.models.user import UserModel

logger = get_logger("vulnova.rbac")


def _resolve_user_role(user: UserModel) -> Role:
    """Safely resolve a UserModel's role string to a Role enum.

    If the role string is invalid or unrecognized, defaults to the lowest
    privilege level (VIEWER) to prevent accidental privilege escalation.
    """
    try:
        return parse_role(user.role)
    except ValueError:
        logger.warning(
            "rbac_unknown_role_defaulting_viewer",
            user_id=str(user.id),
            raw_role=user.role,
        )
        return Role.VIEWER


def require_role(minimum_role: Role) -> Callable[..., Any]:
    """FastAPI dependency factory that enforces a minimum role level.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role(Role.ADMIN))])
        async def admin_endpoint(...): ...

    Args:
        minimum_role: The minimum Role required to access the endpoint.

    Returns:
        A FastAPI dependency function.

    Raises:
        ForbiddenException: If the authenticated user's role is insufficient.
    """

    async def _check_role(
        current_user: UserModel = Depends(get_current_user),
    ) -> UserModel:
        user_role = _resolve_user_role(current_user)

        if not role_meets_minimum(user_role, minimum_role):
            logger.warning(
                "rbac_role_denied",
                user_id=str(current_user.id),
                user_role=current_user.role,
                required_role=minimum_role.name,
            )
            raise ForbiddenException(
                f"Role '{current_user.role}' does not meet minimum "
                f"required role '{minimum_role.name}'",
                details={
                    "required_role": minimum_role.name,
                    "current_role": current_user.role,
                },
            )
        return current_user

    return _check_role


def require_permission(permission: str) -> Callable[..., Any]:
    """FastAPI dependency factory that enforces a specific permission.

    Resolves the permission string to its minimum required role via the
    centralized PERMISSION_MAP and checks the user's role hierarchically.

    Usage:
        @router.post(
            "/scans",
            dependencies=[Depends(require_permission("scans:create"))]
        )
        async def create_scan(...): ...

    Args:
        permission: Permission string (e.g. "scans:create").

    Returns:
        A FastAPI dependency function.

    Raises:
        ForbiddenException: If the authenticated user lacks the permission.
    """

    async def _check_permission(
        current_user: UserModel = Depends(get_current_user),
    ) -> UserModel:
        user_role = _resolve_user_role(current_user)

        if not role_has_permission(user_role, permission):
            logger.warning(
                "rbac_permission_denied",
                user_id=str(current_user.id),
                user_role=current_user.role,
                permission=permission,
            )
            raise ForbiddenException(
                f"Permission '{permission}' denied for role '{current_user.role}'",
                details={
                    "required_permission": permission,
                    "current_role": current_user.role,
                },
            )
        return current_user

    return _check_permission


def require_same_organization(
    target_organization_id: UUID,
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    """FastAPI dependency enforcing tenant isolation.

    Ensures the authenticated user belongs to the same organization as the
    target resource. Never trusts organization_id from request payload alone.

    Usage:
        async def endpoint(
            org_id: UUID,
            user: UserModel = Depends(require_same_organization),
        ): ...

    Note: For inline use, call ``verify_organization_access`` directly.

    Args:
        target_organization_id: The organization_id of the target resource.
        current_user: The authenticated user (injected via Depends).

    Returns:
        The authenticated UserModel if organization matches.

    Raises:
        ForbiddenException: If the user's organization does not match.
    """
    verify_organization_access(current_user, target_organization_id)
    return current_user


def verify_organization_access(user: UserModel, target_organization_id: UUID) -> None:
    """Verify that a user belongs to the target organization.

    This is the imperative version of ``require_same_organization`` for use
    inside service methods or when the target org_id is not available as a
    path parameter.

    Args:
        user: The authenticated UserModel.
        target_organization_id: The organization_id to check against.

    Raises:
        ForbiddenException: If the user's organization does not match.
    """
    if user.organization_id != target_organization_id:
        logger.warning(
            "rbac_tenant_isolation_violation",
            user_id=str(user.id),
            user_org_id=str(user.organization_id),
            target_org_id=str(target_organization_id),
        )
        raise ForbiddenException(
            "Access denied: resource belongs to a different organization",
            details={
                "user_organization_id": str(user.organization_id),
            },
        )
