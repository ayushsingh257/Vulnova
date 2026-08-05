export interface CertificationCategoryResultDTO {
  category_code: string;
  category_name: string;
  status: "PASSED" | "FAILED" | "WARNING";
  pass_rate_percentage: number;
  passed_assertions: number;
  failed_assertions: number;
  total_assertions: number;
  affected_control?: string;
  failure_reason?: string;
  remediation_guidance: string;
}

export interface CertificationValidationSuiteResponse {
  suite_id: string;
  organization_id: string;
  executed_at: string;
  overall_status: "PASSED" | "DEGRADED" | "CRITICAL";
  overall_certification_score: number;
  passed_categories: number;
  failed_categories: number;
  warning_categories: number;
  total_categories: number;
  category_results: CertificationCategoryResultDTO[];
}

export interface CertificationValidationSummaryDTO {
  organization_id: string;
  last_executed_at?: string;
  overall_certification_score: number;
  overall_status: string;
  passed_categories: number;
  failed_categories: number;
}

export class CertificationValidationService {
  private static readonly BASE_URL = "/api/v1/validation/certification";

  /**
   * Execute final Security Control Plane Certification suite.
   */
  public static async runSuite(): Promise<CertificationValidationSuiteResponse> {
    const res = await fetch(`${this.BASE_URL}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) {
      throw new Error(`Failed to run certification validation suite: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Fetch latest Security Certification suite results.
   */
  public static async getResults(): Promise<CertificationValidationSuiteResponse> {
    const res = await fetch(`${this.BASE_URL}/results`);
    if (!res.ok) {
      throw new Error(`Failed to fetch certification validation results: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Fetch enterprise security certification summary.
   */
  public static async getSummary(): Promise<CertificationValidationSummaryDTO> {
    const res = await fetch(`${this.BASE_URL}/summary`);
    if (!res.ok) {
      throw new Error(`Failed to fetch certification validation summary: ${res.statusText}`);
    }
    return res.json();
  }
}
