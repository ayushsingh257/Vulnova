export interface APIValidationCategoryResultDTO {
  category_code: string;
  category_name: string;
  status: "PASSED" | "FAILED" | "WARNING";
  pass_rate_percentage: number;
  passed_assertions: number;
  failed_assertions: number;
  total_assertions: number;
  finding_count: number;
  affected_endpoint?: string;
  affected_subsystem?: string;
  failure_reason?: string;
  remediation_guidance: string;
}

export interface APIValidationSuiteResponse {
  suite_id: string;
  organization_id: string;
  executed_at: string;
  overall_status: "PASSED" | "DEGRADED" | "CRITICAL";
  overall_pass_rate: number;
  passed_categories: number;
  failed_categories: number;
  warning_categories: number;
  total_categories: number;
  category_results: APIValidationCategoryResultDTO[];
}

export interface APIValidationSummaryDTO {
  organization_id: string;
  last_executed_at?: string;
  overall_pass_rate: number;
  overall_status: string;
  passed_categories: number;
  failed_categories: number;
}

export class APISecurityValidationService {
  private static readonly BASE_URL = "/api/v1/validation/api-security";

  /**
   * Execute automated OWASP API Security Top 10 (2023) validation suite.
   */
  public static async runSuite(): Promise<APIValidationSuiteResponse> {
    const res = await fetch(`${this.BASE_URL}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) {
      throw new Error(`Failed to run API security validation suite: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Fetch latest API security validation suite results.
   */
  public static async getResults(): Promise<APIValidationSuiteResponse> {
    const res = await fetch(`${this.BASE_URL}/results`);
    if (!res.ok) {
      throw new Error(`Failed to fetch API security validation results: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Fetch API security verification health summary.
   */
  public static async getSummary(): Promise<APIValidationSummaryDTO> {
    const res = await fetch(`${this.BASE_URL}/summary`);
    if (!res.ok) {
      throw new Error(`Failed to fetch API security validation summary: ${res.statusText}`);
    }
    return res.json();
  }
}
