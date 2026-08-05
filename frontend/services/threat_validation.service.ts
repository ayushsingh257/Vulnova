export interface ThreatCategoryResultDTO {
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

export interface ThreatValidationSuiteResponse {
  suite_id: string;
  organization_id: string;
  executed_at: string;
  overall_status: "PASSED" | "DEGRADED" | "CRITICAL";
  overall_pass_rate: number;
  passed_categories: number;
  failed_categories: number;
  warning_categories: number;
  total_categories: number;
  category_results: ThreatCategoryResultDTO[];
}

export interface ThreatValidationSummaryDTO {
  organization_id: string;
  last_executed_at?: string;
  overall_pass_rate: number;
  overall_status: string;
  passed_categories: number;
  failed_categories: number;
}

export class ThreatValidationService {
  private static readonly BASE_URL = "/api/v1/validation/threat";

  /**
   * Execute automated Threat Model Review & STRIDE Verification Suite.
   */
  public static async runSuite(): Promise<ThreatValidationSuiteResponse> {
    const res = await fetch(`${this.BASE_URL}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) {
      throw new Error(`Failed to run threat validation suite: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Fetch latest Threat Model Security Suite results.
   */
  public static async getResults(): Promise<ThreatValidationSuiteResponse> {
    const res = await fetch(`${this.BASE_URL}/results`);
    if (!res.ok) {
      throw new Error(`Failed to fetch threat validation results: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Fetch Threat Model verification health summary.
   */
  public static async getSummary(): Promise<ThreatValidationSummaryDTO> {
    const res = await fetch(`${this.BASE_URL}/summary`);
    if (!res.ok) {
      throw new Error(`Failed to fetch threat validation summary: ${res.statusText}`);
    }
    return res.json();
  }
}
