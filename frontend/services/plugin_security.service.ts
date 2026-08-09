// Frontend Cryptographically Signed & Sandboxed Plugin Ecosystem Service (Phase 12.7).

export type PluginCapability =
  | "network:http"
  | "network:dns"
  | "network:tcp"
  | "filesystem:read"
  | "filesystem:write"
  | "process:execute";

export type PublisherTrustStatus = "TRUSTED" | "REVOKED" | "PENDING" | "UNTRUSTED";

export type PluginVerificationStatus =
  | "VERIFIED"
  | "UNVERIFIED"
  | "INVALID_SIGNATURE"
  | "REVOKED_PUBLISHER"
  | "UNKNOWN_PUBLISHER"
  | "CAPABILITY_VIOLATION";

export interface PluginManifest {
  plugin_id: string;
  name: string;
  version: string;
  publisher_id: string;
  description?: string;
  entrypoint?: string;
  capabilities: PluginCapability[];
  package_hash: string;
  min_platform_version?: string;
  signature?: string;
}

export interface TrustedPublisher {
  id: string;
  organization_id: string;
  publisher_id: string;
  publisher_name: string;
  public_key_hex: string;
  public_key_fingerprint: string;
  trust_status: PublisherTrustStatus;
  contact_email?: string;
  verified_at?: string;
  revoked_at?: string;
  revocation_reason?: string;
  created_at: string;
}

export interface PluginSignatureVerificationResult {
  plugin_id: string;
  publisher_id: string;
  public_key_fingerprint?: string;
  is_valid: boolean;
  verification_status: PluginVerificationStatus;
  trust_status: PublisherTrustStatus;
  verified_at: string;
  details: Record<string, unknown>;
  error_message?: string;
}

export interface PluginExecutionRequest {
  plugin_id: string;
  target_url: string;
  scan_context?: Record<string, unknown>;
  timeout_seconds?: number;
  memory_limit_mb?: number;
  cpu_limit?: number;
}

export interface PluginExecutionResult {
  execution_id: string;
  plugin_id: string;
  status: "SUCCESS" | "BLOCKED" | "TIMEOUT" | "FAILED" | "PERMISSION_DENIED";
  findings_count: number;
  findings: Array<Record<string, unknown>>;
  duration_ms: number;
  exit_code: number;
  sandbox_driver: string;
  capabilities_used: string[];
  error?: string;
}

export interface PluginSecurityReport {
  plugin_id: string;
  name: string;
  version: string;
  publisher_id: string;
  publisher_name: string;
  signature_valid: boolean;
  trust_status: PublisherTrustStatus;
  capabilities: PluginCapability[];
  sandbox_enforced: boolean;
  last_verified_at?: string;
  total_executions: number;
  blocked_executions: number;
  created_at?: string;
}

export class PluginSecurityService {
  private static baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

  private static getHeaders(token?: string): HeadersInit {
    const headers: HeadersInit = { "Content-Type": "application/json" };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    return headers;
  }

  static async verifyPlugin(
    pluginId: string,
    manifest: PluginManifest,
    signatureHex: string,
    token?: string
  ): Promise<PluginSignatureVerificationResult> {
    const res = await fetch(`${this.baseUrl}/plugins/${pluginId}/verify`, {
      method: "POST",
      headers: this.getHeaders(token),
      body: JSON.stringify({ manifest, signature_hex: signatureHex }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Plugin verification failed" }));
      throw new Error(err.detail || "Failed to verify plugin signature");
    }
    return res.json();
  }

  static async listTrustedPublishers(
    status?: string,
    token?: string
  ): Promise<TrustedPublisher[]> {
    const url = status
      ? `${this.baseUrl}/plugins/trusted?status=${encodeURIComponent(status)}`
      : `${this.baseUrl}/plugins/trusted`;
    const res = await fetch(url, {
      method: "GET",
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      throw new Error("Failed to fetch trusted publishers");
    }
    return res.json();
  }

  static async registerTrustedPublisher(
    publisher: {
      publisher_id: string;
      publisher_name: string;
      public_key_hex: string;
      contact_email?: string;
    },
    token?: string
  ): Promise<TrustedPublisher> {
    const res = await fetch(`${this.baseUrl}/plugins/trust`, {
      method: "POST",
      headers: this.getHeaders(token),
      body: JSON.stringify(publisher),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Registration failed" }));
      throw new Error(err.detail || "Failed to register trusted publisher");
    }
    return res.json();
  }

  static async revokeTrustedPublisher(
    publisherId: string,
    reason: string,
    token?: string
  ): Promise<TrustedPublisher> {
    const res = await fetch(
      `${this.baseUrl}/plugins/trust/${publisherId}?reason=${encodeURIComponent(reason)}`,
      {
        method: "DELETE",
        headers: this.getHeaders(token),
      }
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Revocation failed" }));
      throw new Error(err.detail || "Failed to revoke publisher trust");
    }
    return res.json();
  }

  static async executePlugin(
    req: PluginExecutionRequest,
    token?: string
  ): Promise<PluginExecutionResult> {
    const res = await fetch(`${this.baseUrl}/plugins/${req.plugin_id}/execute`, {
      method: "POST",
      headers: this.getHeaders(token),
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Execution failed" }));
      throw new Error(err.detail || "Failed to execute sandboxed plugin");
    }
    return res.json();
  }

  static async getSecurityReport(
    pluginId: string,
    token?: string
  ): Promise<PluginSecurityReport> {
    const res = await fetch(`${this.baseUrl}/plugins/${pluginId}/security-report`, {
      method: "GET",
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      throw new Error("Failed to fetch plugin security report");
    }
    return res.json();
  }
}
