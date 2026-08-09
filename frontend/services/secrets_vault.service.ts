// Frontend Enterprise Secrets Vault & KMS Credential Governance Service (Phase 12.8).

export type KMSProviderType = "local" | "vault" | "aws_kms" | "gcp_kms";

export type SecretType =
  | "INTEGRATION_TOKEN"
  | "API_KEY"
  | "CLOUD_CREDENTIAL"
  | "CERTIFICATE"
  | "GENERIC";

export type SecretStatus = "ACTIVE" | "ROTATED" | "REVOKED" | "EXPIRED";

export interface CreateSecretRequest {
  secret_name: string;
  secret_type?: SecretType;
  plaintext_value: string;
  rotation_interval_days?: number;
  metadata?: Record<string, unknown>;
  expires_in_days?: number;
}

export interface SecretResponse {
  id: string;
  organization_id: string;
  secret_name: string;
  secret_type: SecretType;
  provider: string;
  masked_value: string;
  key_version: number;
  status: SecretStatus;
  metadata: Record<string, unknown>;
  rotation_interval_days: number;
  last_rotated_at?: string;
  next_rotation_due?: string;
  expires_at?: string;
  created_at: string;
  updated_at: string;
}

export interface SecretDecrypted {
  id: string;
  secret_name: string;
  secret_type: SecretType;
  plaintext_value: string;
  key_version: number;
  accessed_at: string;
}

export interface RotateSecretRequest {
  new_plaintext_value?: string;
  reason?: string;
}

export interface SecretRotationStatus {
  total_secrets: number;
  active_rotations: number;
  due_in_7_days: number;
  due_in_30_days: number;
  overdue_rotations: number;
  active_provider: string;
}

export interface KMSHealth {
  provider: string;
  is_healthy: boolean;
  kek_id: string;
  latency_ms: number;
  details: Record<string, unknown>;
  checked_at: string;
}

export class SecretsVaultService {
  private static baseUrl = "/api/v1/secrets";

  private static getHeaders(token?: string): HeadersInit {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    return headers;
  }

  /**
   * Store a new envelope-encrypted secret in the enterprise vault.
   */
  static async storeSecret(
    payload: CreateSecretRequest,
    token?: string
  ): Promise<SecretResponse> {
    const res = await fetch(`${this.baseUrl}`, {
      method: "POST",
      headers: this.getHeaders(token),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to store secret" }));
      throw new Error(err.detail || "Failed to store secret");
    }
    return res.json();
  }

  /**
   * List all secrets metadata in organization.
   */
  static async listSecrets(
    status?: string,
    skip: number = 0,
    limit: number = 50,
    token?: string
  ): Promise<SecretResponse[]> {
    const params = new URLSearchParams();
    if (status) params.append("status", status);
    params.append("skip", String(skip));
    params.append("limit", String(limit));

    const res = await fetch(`${this.baseUrl}?${params.toString()}`, {
      method: "GET",
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      throw new Error("Failed to list secrets");
    }
    return res.json();
  }

  /**
   * Retrieve single secret metadata and rotation policy.
   */
  static async getSecretMetadata(
    id: string,
    token?: string
  ): Promise<SecretResponse> {
    const res = await fetch(`${this.baseUrl}/${id}`, {
      method: "GET",
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      throw new Error("Failed to get secret metadata");
    }
    return res.json();
  }

  /**
   * Access plaintext secret (requires admin authorization).
   */
  static async accessSecretPlaintext(
    id: string,
    token?: string
  ): Promise<SecretDecrypted> {
    const res = await fetch(`${this.baseUrl}/${id}/access`, {
      method: "POST",
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Access denied" }));
      throw new Error(err.detail || "Failed to access secret");
    }
    return res.json();
  }

  /**
   * Rotate a secret on-demand.
   */
  static async rotateSecret(
    id: string,
    payload: RotateSecretRequest,
    token?: string
  ): Promise<SecretResponse> {
    const res = await fetch(`${this.baseUrl}/${id}/rotate`, {
      method: "POST",
      headers: this.getHeaders(token),
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      throw new Error("Failed to rotate secret");
    }
    return res.json();
  }

  /**
   * Delete / Revoke a secret from the vault.
   */
  static async deleteSecret(id: string, token?: string): Promise<void> {
    const res = await fetch(`${this.baseUrl}/${id}`, {
      method: "DELETE",
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      throw new Error("Failed to delete secret");
    }
  }

  /**
   * Get rotation health and posture summary.
   */
  static async getRotationStatus(token?: string): Promise<SecretRotationStatus> {
    const res = await fetch(`${this.baseUrl}/rotation-status`, {
      method: "GET",
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      throw new Error("Failed to get rotation status");
    }
    return res.json();
  }

  /**
   * List supported KMS provider drivers.
   */
  static async listProviders(token?: string): Promise<string[]> {
    const res = await fetch(`${this.baseUrl}/providers`, {
      method: "GET",
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      throw new Error("Failed to list KMS providers");
    }
    return res.json();
  }

  /**
   * Check KMS provider health diagnoses.
   */
  static async getKmsHealth(token?: string): Promise<KMSHealth[]> {
    const res = await fetch(`${this.baseUrl}/kms-health`, {
      method: "GET",
      headers: this.getHeaders(token),
    });
    if (!res.ok) {
      throw new Error("Failed to get KMS health status");
    }
    return res.json();
  }
}
