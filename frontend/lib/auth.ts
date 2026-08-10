export type UserRole = "OWNER" | "ADMIN" | "SECURITY_ANALYST" | "VIEWER";

export interface UserProfile {
  email: string;
  role: UserRole;
  organization: string;
  organizationId: string;
  permissions: string[];
}

export const ROLE_PERMISSIONS: Record<UserRole, string[]> = {
  OWNER: [
    "dashboard:read",
    "scans:read",
    "scans:write",
    "scans:delete",
    "findings:read",
    "findings:write",
    "assets:read",
    "assets:write",
    "reports:read",
    "reports:export",
    "compliance:read",
    "validation:read",
    "validation:execute",
    "integrations:read",
    "integrations:write",
    "users:read",
    "users:write",
    "roles:read",
    "roles:write",
    "secrets:read",
    "secrets:write",
    "admin:access",
    "audit:read",
  ],
  ADMIN: [
    "dashboard:read",
    "scans:read",
    "scans:write",
    "findings:read",
    "findings:write",
    "assets:read",
    "assets:write",
    "reports:read",
    "reports:export",
    "compliance:read",
    "validation:read",
    "validation:execute",
    "integrations:read",
    "integrations:write",
    "users:read",
    "users:write",
    "roles:read",
    "secrets:read",
    "secrets:write",
  ],
  SECURITY_ANALYST: [
    "dashboard:read",
    "scans:read",
    "scans:write",
    "findings:read",
    "findings:write",
    "assets:read",
    "assets:write",
    "reports:read",
    "reports:export",
    "compliance:read",
    "validation:read",
    "validation:execute",
  ],
  VIEWER: [
    "dashboard:read",
    "findings:read",
    "assets:read",
    "reports:read",
    "reports:export",
    "compliance:read",
    "validation:read",
  ],
};

// Route protection matrix defining minimum required role per route prefix
export const ROUTE_ROLE_REQUIREMENTS: Array<{ prefix: string; allowedRoles: UserRole[] }> = [
  { prefix: "/admin", allowedRoles: ["OWNER"] },
  { prefix: "/settings/users", allowedRoles: ["OWNER", "ADMIN"] },
  { prefix: "/settings/roles", allowedRoles: ["OWNER", "ADMIN"] },
  { prefix: "/settings/api-keys", allowedRoles: ["OWNER", "ADMIN"] },
  { prefix: "/settings/secrets", allowedRoles: ["OWNER", "ADMIN"] },
  { prefix: "/database/performance", allowedRoles: ["OWNER", "ADMIN"] },
  { prefix: "/security/mfa", allowedRoles: ["OWNER", "ADMIN"] },
  { prefix: "/security/quarantine", allowedRoles: ["OWNER", "ADMIN", "SECURITY_ANALYST"] },
  { prefix: "/scans", allowedRoles: ["OWNER", "ADMIN", "SECURITY_ANALYST"] },
  { prefix: "/schedules", allowedRoles: ["OWNER", "ADMIN", "SECURITY_ANALYST"] },
  { prefix: "/validation/pentest", allowedRoles: ["OWNER", "ADMIN", "SECURITY_ANALYST"] },
];

/**
 * Get current user profile from localStorage with fallback defaults.
 */
export function getCurrentUser(): UserProfile {
  if (typeof window === "undefined") {
    return {
      email: "analyst@enterprise-corp.com",
      role: "SECURITY_ANALYST",
      organization: "Acme Corp Enterprise",
      organizationId: "org-acme-001",
      permissions: ROLE_PERMISSIONS["SECURITY_ANALYST"],
    };
  }

  try {
    const raw = localStorage.getItem("user");
    if (raw) {
      const parsed = JSON.parse(raw);
      const role: UserRole = (parsed.role as UserRole) || "SECURITY_ANALYST";
      return {
        email: parsed.email || "analyst@enterprise-corp.com",
        role: role,
        organization: parsed.organization || "Acme Corp Enterprise",
        organizationId: parsed.organizationId || "org-acme-001",
        permissions: ROLE_PERMISSIONS[role] || ROLE_PERMISSIONS["SECURITY_ANALYST"],
      };
    }
  } catch (e) {
    console.warn("Failed to parse user from localStorage:", e);
  }

  return {
    email: "analyst@enterprise-corp.com",
    role: "SECURITY_ANALYST",
    organization: "Acme Corp Enterprise",
    organizationId: "org-acme-001",
    permissions: ROLE_PERMISSIONS["SECURITY_ANALYST"],
  };
}

/**
 * Set active role for local testing and store in localStorage.
 * Role switching is strictly disabled in production builds (NODE_ENV === 'production').
 */
export function setCurrentRole(role: UserRole): UserProfile {
  const current = getCurrentUser();
  if (process.env.NODE_ENV === "production") {
    console.warn("Role switching is disabled in production mode.");
    return current;
  }
  const updated: UserProfile = {
    ...current,
    role,
    permissions: ROLE_PERMISSIONS[role] || [],
  };
  if (typeof window !== "undefined") {
    localStorage.setItem("user", JSON.stringify(updated));
  }
  return updated;
}

/**
 * Check if the user's role is allowed to access a specific pathname.
 */
export function isRouteAllowed(pathname: string, userRole: UserRole): boolean {
  const rule = ROUTE_ROLE_REQUIREMENTS.find((r) => pathname.startsWith(r.prefix));
  if (!rule) return true; // Default allow for general routes like /dashboard, /findings, /assets
  return rule.allowedRoles.includes(userRole);
}
