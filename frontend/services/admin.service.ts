// Frontend Admin Control Plane Service Module

export interface OrganizationAdmin {
  id: string;
  name: string;
  slug: string;
  plan_tier: string;
  is_active: boolean;
  member_count: number;
  total_scans_count: number;
  total_findings_count: number;
  active_api_keys_count: number;
  created_at: string;
  updated_at: string;
}

export interface UserAdminItem {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  is_mfa_enabled: boolean;
  created_at: string;
}

export interface UserAdminListResponse {
  total_count: number;
  users: UserAdminItem[];
}

export interface InviteUserAdminRequest {
  email: string;
  full_name: string;
  role: string;
}

export interface UpdateUserRoleAdminRequest {
  role: string;
}

export interface PermissionBoundary {
  permission_key: string;
  description: string;
  minimum_role: string;
}

export interface RolePermissionBoundary {
  role_name: string;
  role_level: number;
  description: string;
  granted_permissions: string[];
}

export interface RolePermissionMatrixResponse {
  roles: RolePermissionBoundary[];
  permissions: PermissionBoundary[];
}

export interface APIKeyAdminItem {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  created_by_user_id?: string;
  created_at: string;
  expires_at?: string;
  last_used_at?: string;
  is_active: boolean;
}

export interface APIKeyAdminListResponse {
  total_count: number;
  api_keys: APIKeyAdminItem[];
}

export interface CreateAPIKeyAdminRequest {
  name: string;
  scopes: string[];
  expires_in_days?: number;
}

export interface CreateAPIKeyAdminResponse {
  id: string;
  name: string;
  raw_api_key: string;
  key_prefix: string;
  scopes: string[];
  created_at: string;
  expires_at?: string;
}

export interface SecurityOverviewAdmin {
  organization_id: string;
  total_users_count: number;
  mfa_enrolled_count: number;
  mfa_enforcement_status: string;
  session_security_policy: string;
  audit_logging_enabled: boolean;
  last_security_audit_at: string;
}

export class AdminService {
  private static BASE_URL = "/api/v1/admin";

  public static async getOrganizationProfile(): Promise<OrganizationAdmin> {
    const res = await fetch(`${this.BASE_URL}/organization`);
    if (!res.ok) {
      throw new Error(`Failed to fetch organization profile: ${res.statusText}`);
    }
    return res.json();
  }

  public static async updateOrganizationProfile(
    name?: string,
    planTier?: string
  ): Promise<OrganizationAdmin> {
    const res = await fetch(`${this.BASE_URL}/organization`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, plan_tier: planTier }),
    });
    if (!res.ok) {
      throw new Error(`Failed to update organization: ${res.statusText}`);
    }
    return res.json();
  }

  public static async listUsers(): Promise<UserAdminListResponse> {
    const res = await fetch(`${this.BASE_URL}/users`);
    if (!res.ok) {
      throw new Error(`Failed to fetch organization users: ${res.statusText}`);
    }
    return res.json();
  }

  public static async inviteUser(
    req: InviteUserAdminRequest
  ): Promise<UserAdminItem> {
    const res = await fetch(`${this.BASE_URL}/users/invite`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      throw new Error(`Failed to invite team member: ${res.statusText}`);
    }
    return res.json();
  }

  public static async updateUserRole(
    userId: string,
    role: string
  ): Promise<UserAdminItem> {
    const res = await fetch(`${this.BASE_URL}/users/${userId}/role`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role }),
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Failed to update user role: ${res.statusText}`);
    }
    return res.json();
  }

  public static async deactivateUser(userId: string): Promise<UserAdminItem> {
    const res = await fetch(`${this.BASE_URL}/users/${userId}`, {
      method: "DELETE",
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Failed to deactivate user: ${res.statusText}`);
    }
    return res.json();
  }

  public static async getRolePermissionMatrix(): Promise<RolePermissionMatrixResponse> {
    const res = await fetch(`${this.BASE_URL}/roles`);
    if (!res.ok) {
      throw new Error(`Failed to fetch role matrix: ${res.statusText}`);
    }
    return res.json();
  }

  public static async listAPIKeys(): Promise<APIKeyAdminListResponse> {
    const res = await fetch(`${this.BASE_URL}/api-keys`);
    if (!res.ok) {
      throw new Error(`Failed to fetch API keys: ${res.statusText}`);
    }
    return res.json();
  }

  public static async createAPIKey(
    req: CreateAPIKeyAdminRequest
  ): Promise<CreateAPIKeyAdminResponse> {
    const res = await fetch(`${this.BASE_URL}/api-keys`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      throw new Error(`Failed to generate API key: ${res.statusText}`);
    }
    return res.json();
  }

  public static async revokeAPIKey(keyId: string): Promise<void> {
    const res = await fetch(`${this.BASE_URL}/api-keys/${keyId}`, {
      method: "DELETE",
    });
    if (!res.ok) {
      throw new Error(`Failed to revoke API key: ${res.statusText}`);
    }
  }

  public static async getSecurityOverview(): Promise<SecurityOverviewAdmin> {
    const res = await fetch(`${this.BASE_URL}/security/status`);
    if (!res.ok) {
      throw new Error(`Failed to fetch security overview: ${res.statusText}`);
    }
    return res.json();
  }
}
