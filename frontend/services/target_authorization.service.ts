// Frontend Target Ownership Verification & Scan Authorization Service Module.

export interface TargetVerificationChallenge {
  id: string;
  target_id: string;
  organization_id: string;
  challenge_token: string;
  verification_type: "DNS_TXT" | "HTTP_WELL_KNOWN";
  status: "PENDING" | "VERIFIED" | "FAILED" | "EXPIRED";
  verification_metadata?: Record<string, any>;
  created_at: string;
  verified_at?: string;
  expires_at: string;
  instructions?: string;
}

export interface TargetVerificationResult {
  challenge_id: string;
  target_id: string;
  verified: boolean;
  status: string;
  message: string;
  verified_at?: string;
  evidence?: Record<string, any>;
}

export interface ScanApprovalRequest {
  id: string;
  organization_id: string;
  scan_job_id?: string;
  target_id: string;
  requested_by: string;
  approved_by?: string;
  status: "REQUESTED" | "PENDING_APPROVAL" | "APPROVED" | "REJECTED";
  reason?: string;
  rejection_reason?: string;
  created_at: string;
  updated_at: string;
}

export class TargetAuthorizationService {
  public static async verifyTarget(
    targetId: string,
    challengeType?: string
  ): Promise<TargetVerificationResult> {
    const query = challengeType ? `?challenge_type=${challengeType}` : "";
    const res = await fetch(`/api/v1/targets/${targetId}/verify${query}`, {
      method: "POST",
    });
    if (!res.ok) {
      throw new Error(`Target verification failed: ${res.statusText}`);
    }
    return res.json();
  }

  public static async getVerificationStatus(
    targetId: string
  ): Promise<TargetVerificationChallenge> {
    const res = await fetch(`/api/v1/targets/${targetId}/verification-status`);
    if (!res.ok) {
      throw new Error(`Failed to fetch verification status: ${res.statusText}`);
    }
    return res.json();
  }

  public static async approveScanRequest(
    requestId: string,
    reason?: string
  ): Promise<ScanApprovalRequest> {
    const query = reason ? `?reason=${encodeURIComponent(reason)}` : "";
    const res = await fetch(`/api/v1/scan-approvals/${requestId}/approve${query}`, {
      method: "POST",
    });
    if (!res.ok) {
      throw new Error(`Failed to approve scan request: ${res.statusText}`);
    }
    return res.json();
  }

  public static async rejectScanRequest(
    requestId: string,
    reason: string
  ): Promise<ScanApprovalRequest> {
    const query = `?reason=${encodeURIComponent(reason)}`;
    const res = await fetch(`/api/v1/scan-approvals/${requestId}/reject${query}`, {
      method: "POST",
    });
    if (!res.ok) {
      throw new Error(`Failed to reject scan request: ${res.statusText}`);
    }
    return res.json();
  }
}
