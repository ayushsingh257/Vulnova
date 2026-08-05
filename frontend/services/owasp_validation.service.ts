export interface OWASPCategoryResultDTO {
  category_code: string;
  category_name: string;
  status: "PASSED" | "FAILED" | "WARNING";
  pass_rate_percentage: number;
  passed_assertions: number;
  failed_assertions: number;
  total_assertions: number;
  finding_count: number;
  affected_finding_ids: string[];
  failure_reason?: string;
  affected_subsystem?: string;
  remediation_guidance: string;
}

export interface OWASPValidationSuiteResponse {
  suite_id: string;
  organization_id: string;
  executed_at: string;
  overall_status: "PASSED" | "DEGRADED" | "CRITICAL";
  overall_pass_rate: number;
  passed_categories: number;
  failed_categories: number;
  warning_categories: number;
  total_categories: number;
  category_results: OWASPCategoryResultDTO[];
}

export interface OWASPVerificationSummaryDTO {
  organization_id: string;
  last_executed_at?: string;
  overall_pass_rate: number;
  overall_status: string;
  passed_categories: number;
  failed_categories: number;
}

export class OWASPValidationService {
  private static readonly BASE_URL = "/api/v1/validation/owasp-top-10";

  /**
   * Execute automated OWASP Top 10 (2021) security validation suite.
   */
  public static async runSuite(): Promise<OWASPValidationSuiteResponse> {
    const res = await fetch(`${this.BASE_URL}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) {
      throw new Error(`Failed to run OWASP validation suite: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Fetch latest OWASP validation suite results.
   */
  public static async getResults(): Promise<OWASPValidationSuiteResponse> {
    const res = await fetch(`${this.BASE_URL}/results`);
    if (!res.ok) {
      throw new Error(`Failed to fetch OWASP validation results: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Fetch OWASP verification health summary.
   */
  public static async getSummary(): Promise<OWASPVerificationSummaryDTO> {
    const res = await fetch(`${this.BASE_URL}/summary`);
    if (!res.ok) {
      throw new Error(`Failed to fetch OWASP validation summary: ${res.statusText}`);
    }
    return res.json();
  }
}
