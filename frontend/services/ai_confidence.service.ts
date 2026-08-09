// Frontend AI Finding Confidence & Remediation Governance Service (Phase 12.6).

export type ConfidenceLevel = "LOW" | "MEDIUM" | "HIGH" | "CONFIRMED";

export type VerificationStatus =
  | "UNVERIFIED"
  | "VERIFYING"
  | "CONFIRMED"
  | "FALSE_POSITIVE"
  | "NEEDS_REVIEW";

export type ReviewDecision =
  | "CONFIRM"
  | "FALSE_POSITIVE"
  | "ACCEPT_RISK"
  | "REQUEST_MORE_EVIDENCE";

export type RemediationApprovalState =
  | "AI_RECOMMENDED"
  | "ANALYST_REVIEW"
  | "APPROVED_FOR_IMPLEMENTATION"
  | "IMPLEMENTED"
  | "VERIFIED"
  | "REJECTED";

export interface FindingConfidenceResult {
  finding_id: string;
  confidence_score: number;
  confidence_level: ConfidenceLevel;
  evidence_quality_score: number;
  reproduction_score: number;
  ai_analysis_score: number;
  verification_status: VerificationStatus;
  explanation: string;
}

export interface FindingVerificationAttempt {
  id: string;
  organization_id: string;
  finding_id: string;
  verification_status: VerificationStatus;
  strategy: string;
  probe_response_status?: number;
  probe_output?: string;
  is_reproduced: boolean;
  created_at: string;
}

export interface FindingReview {
  id: string;
  organization_id: string;
  finding_id: string;
  reviewer_id: string;
  decision: ReviewDecision;
  comments?: string;
  evidence_snapshot?: string;
  created_at: string;
}

export interface RemediationApproval {
  id: string;
  organization_id: string;
  remediation_plan_id: string;
  finding_id: string;
  previous_state: string;
  new_state: RemediationApprovalState;
  action_by: string;
  notes?: string;
  created_at: string;
}

export class AIConfidenceService {
  private static BASE_URL = "/api/v1";

  /**
   * Calculate and retrieve multi-dimensional confidence score for a finding.
   */
  public static async getConfidence(
    findingId: string
  ): Promise<FindingConfidenceResult> {
    const res = await fetch(`${this.BASE_URL}/findings/${findingId}/confidence`);
    if (!res.ok) {
      throw new Error(
        `Failed to fetch finding confidence: ${res.statusText}`
      );
    }
    return res.json();
  }

  /**
   * Execute automated safe re-probe verification for a finding.
   */
  public static async verifyFinding(
    findingId: string
  ): Promise<FindingVerificationAttempt> {
    const res = await fetch(
      `${this.BASE_URL}/findings/${findingId}/verify`,
      { method: "POST" }
    );
    if (!res.ok) {
      throw new Error(
        `Failed to verify finding: ${res.statusText}`
      );
    }
    return res.json();
  }

  /**
   * Submit a human analyst review decision for a finding.
   */
  public static async reviewFinding(
    findingId: string,
    decision: ReviewDecision,
    comments?: string
  ): Promise<FindingReview> {
    const res = await fetch(
      `${this.BASE_URL}/findings/${findingId}/review`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, comments }),
      }
    );
    if (!res.ok) {
      throw new Error(
        `Failed to submit finding review: ${res.statusText}`
      );
    }
    return res.json();
  }

  /**
   * Approve an AI-recommended remediation plan for implementation.
   * Human approval required — AI cannot execute remediation autonomously.
   */
  public static async approveRemediation(
    remediationId: string,
    notes?: string
  ): Promise<RemediationApproval> {
    const url = new URL(
      `${this.BASE_URL}/remediation/${remediationId}/approve`,
      window.location.origin
    );
    if (notes) url.searchParams.set("notes", notes);
    const res = await fetch(url.toString(), { method: "POST" });
    if (!res.ok) {
      throw new Error(
        `Failed to approve remediation: ${res.statusText}`
      );
    }
    return res.json();
  }

  /**
   * Reject an AI-recommended remediation plan.
   */
  public static async rejectRemediation(
    remediationId: string,
    notes?: string
  ): Promise<RemediationApproval> {
    const url = new URL(
      `${this.BASE_URL}/remediation/${remediationId}/reject`,
      window.location.origin
    );
    if (notes) url.searchParams.set("notes", notes);
    const res = await fetch(url.toString(), { method: "POST" });
    if (!res.ok) {
      throw new Error(
        `Failed to reject remediation: ${res.statusText}`
      );
    }
    return res.json();
  }
}
