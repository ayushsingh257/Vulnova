"""Domain Entity: Role Hierarchy & Permission Map.

Pure domain definitions for Vulnova RBAC system.
No framework, database, or HTTP dependencies.
"""

from enum import IntEnum, unique
from typing import Dict, FrozenSet


@unique
class Role(IntEnum):
    """Vulnova Organization Role Hierarchy.

    Roles are ordered by privilege level (higher value = more privilege).
    A higher role implicitly holds all permissions of lower roles.

    Compatible with existing VARCHAR(50) database column via string labels.
    """

    VIEWER = 10
    SECURITY_ANALYST = 20
    ADMIN = 30
    OWNER = 40


# ── Role label ↔ enum mapping ──────────────────────────

ROLE_LABELS: Dict[str, Role] = {
    "VIEWER": Role.VIEWER,
    "SECURITY_ANALYST": Role.SECURITY_ANALYST,
    "ADMIN": Role.ADMIN,
    "OWNER": Role.OWNER,
}

ROLE_NAMES: Dict[Role, str] = {v: k for k, v in ROLE_LABELS.items()}


def parse_role(role_str: str) -> Role:
    """Parse a role string label into a Role enum member.

    Args:
        role_str: Role string label (e.g. "ADMIN", "VIEWER").

    Returns:
        Corresponding Role enum member.

    Raises:
        ValueError: If role_str is not a recognized role label.
    """
    role = ROLE_LABELS.get(role_str.upper().strip())
    if role is None:
        raise ValueError(
            f"Unknown role '{role_str}'. "
            f"Valid roles: {', '.join(sorted(ROLE_LABELS.keys()))}"
        )
    return role


# ── Permission definitions ─────────────────────────────
#
# Permissions follow the pattern "resource:action".
# Each permission maps to the MINIMUM role required to perform it.
# Higher roles inherit all permissions of lower roles automatically.

PERMISSION_MAP: Dict[str, Role] = {
    # ── Organization Management ──
    "organization:read": Role.VIEWER,
    "organization:update": Role.ADMIN,
    "organization:delete": Role.OWNER,
    "organization:manage_billing": Role.OWNER,
    # ── User Management ──
    "users:read": Role.ADMIN,
    "users:invite": Role.ADMIN,
    "users:update_role": Role.OWNER,
    "users:remove": Role.ADMIN,
    # ── Scan Targets ──
    "targets:read": Role.VIEWER,
    "targets:create": Role.SECURITY_ANALYST,
    "targets:update": Role.SECURITY_ANALYST,
    "targets:delete": Role.ADMIN,
    # ── Scan Jobs ──
    "scans:read": Role.VIEWER,
    "scans:create": Role.SECURITY_ANALYST,
    "scans:cancel": Role.SECURITY_ANALYST,
    "scans:delete": Role.ADMIN,
    # ── Asset Inventory ──
    "assets:read": Role.VIEWER,
    # ── Findings & Triage ──
    "findings:read": Role.VIEWER,
    "findings:triage": Role.SECURITY_ANALYST,
    "findings:suppress": Role.ADMIN,
    "findings:ai_analyze": Role.SECURITY_ANALYST,
    "findings:ai_explain": Role.SECURITY_ANALYST,
    "findings:export": Role.SECURITY_ANALYST,
    # ── Reports ──
    "reports:read": Role.VIEWER,
    "reports:generate": Role.SECURITY_ANALYST,
    "reports:export": Role.SECURITY_ANALYST,
    # ── API Keys ──
    "api_keys:read": Role.ADMIN,
    "api_keys:create": Role.ADMIN,
    "api_keys:revoke": Role.ADMIN,
    # ── Integrations & Webhooks ──
    "integrations:read": Role.ADMIN,
    "integrations:manage": Role.ADMIN,
    # ── Audit Logs ──
    "audit_logs:read": Role.ADMIN,
}

ALL_PERMISSIONS: FrozenSet[str] = frozenset(PERMISSION_MAP.keys())


def role_has_permission(role: Role, permission: str) -> bool:
    """Check if a role has a specific permission.

    The check uses hierarchical inheritance: a role with a higher privilege
    level automatically satisfies permissions requiring a lower role.

    Args:
        role: The user's Role enum value.
        permission: Permission string (e.g. "scans:create").

    Returns:
        True if the role is sufficient for the permission, False otherwise.
    """
    required_role = PERMISSION_MAP.get(permission)
    if required_role is None:
        # Unknown permission → deny by default (fail-closed)
        return False
    return role >= required_role


def role_meets_minimum(role: Role, minimum_role: Role) -> bool:
    """Check if a role meets or exceeds the minimum required role.

    Args:
        role: The user's current role.
        minimum_role: The minimum role required.

    Returns:
        True if role >= minimum_role.
    """
    return role >= minimum_role
