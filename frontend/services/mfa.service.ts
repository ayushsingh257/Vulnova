export interface MFASetupResponse {
  secret: string;
  provisioning_uri: string;
  qr_code_base64: string;
  recovery_codes: string[];
}

export interface MFAStatusResponse {
  mfa_enabled: boolean;
  mfa_verified_at?: string;
  mfa_last_used_at?: string;
  backup_codes_remaining: number;
}

export interface MFARecoveryRegenerateResponse {
  recovery_codes: string[];
}

export class MFAService {
  private static readonly BASE_URL = "/api/v1/auth/mfa";

  /**
   * Initiate MFA setup to receive TOTP secret, provisioning URI, QR code Base64, and backup codes.
   */
  public static async initiateSetup(): Promise<MFASetupResponse> {
    const res = await fetch(`${this.BASE_URL}/setup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to initiate MFA setup.");
    }
    return res.json();
  }

  /**
   * Verify first OTP code and activate MFA on account.
   */
  public static async verifySetup(code: string): Promise<{ status: string; message: string }> {
    const res = await fetch(`${this.BASE_URL}/verify-setup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Invalid OTP verification code.");
    }
    return res.json();
  }

  /**
   * Disable MFA requiring current password and valid OTP.
   */
  public static async disableMFA(current_password: string, code: string): Promise<{ status: string; message: string }> {
    const res = await fetch(`${this.BASE_URL}/disable`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_password, code }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to disable MFA.");
    }
    return res.json();
  }

  /**
   * Verify OTP or single-use recovery code during login challenge.
   */
  public static async challenge(mfa_login_token: string, code: string): Promise<any> {
    const res = await fetch(`${this.BASE_URL}/challenge`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mfa_login_token, code }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Invalid authentication code.");
    }
    return res.json();
  }

  /**
   * Regenerate new backup recovery codes.
   */
  public static async regenerateRecoveryCodes(current_password: string, code: string): Promise<MFARecoveryRegenerateResponse> {
    const res = await fetch(`${this.BASE_URL}/recovery-codes/regenerate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_password, code }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to regenerate recovery codes.");
    }
    return res.json();
  }

  /**
   * Fetch current MFA status.
   */
  public static async getStatus(): Promise<MFAStatusResponse> {
    const res = await fetch(`${this.BASE_URL}/status`);
    if (!res.ok) {
      throw new Error("Failed to fetch MFA status.");
    }
    return res.json();
  }
}
