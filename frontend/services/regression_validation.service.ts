export interface RegressionCategoryResultDTO {
  category_code: string;
  category_name: string;
  status: "PASSED" | "FAILED" | "WARNING";
  pass_rate_percentage: number;
  passed_assertions: number;
  failed_assertions: number;
  total_assertions: number;
  finding_count: number;
  affected_component?: string;
  failure_reason?: string;
  remediation_guidance: string;
}

export interface RegressionValidationSuiteResponse {
  suite_id: string;
  organization_id: string;
  executed_at: string;
  overall_status: "PASSED" | "DEGRADED" | "CRITICAL";
  overall_pass_rate: number;
  passed_categories: number;
  failed_categories: number;
  warning_categories: number;
  total_categories: number;
  category_results: RegressionCategoryResultDTO[];
}

export interface RegressionValidationSummaryDTO {
  organization_id: string;
  last_executed_at?: string;
  overall_pass_rate: number;
  overall_status: string;
  passed_categories: number;
  failed_categories: number;
}

export class RegressionValidationService {
  private static readonly BASE_URL = "/api/v1/validation/regression";

  /**
   * Execute automated Security Regression Testing Suite.
   */
  public static async runSuite(): Promise<RegressionValidationSuiteResponse> {
    const res = await fetch(`${this.BASE_URL}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) {
      throw new Error(`Failed to run regression validation suite: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Fetch latest Security Regression Suite results.
   */
  public static async getResults(): Promise<RegressionValidationSuiteResponse> {
    const res = await fetch(`${this.BASE_URL}/results`);
    if (!res.ok) {
      throw new Error(`Failed to fetch regression validation results: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Fetch Security Regression verification health summary.
   */
  public static async getSummary(): Promise<RegressionValidationSummaryDTO> {
    const res = await fetch(`${this.BASE_URL}/summary`);
    if (!res.ok) {
      throw new Error(`Failed to fetch regression validation summary: ${res.statusText}`);
    }
    return res.json();
  }
}
