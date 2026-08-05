export interface CreateExecutiveReportRequest {
  title?: string;
  timeframe_days?: number;
  include_sections?: string[];
}

export interface ExecutiveReportMetadataResponse {
  id: string;
  organization_id: string;
  title: string;
  generated_at: string;
  posture_score: number;
  posture_status: "SECURE" | "ELEVATED_RISK" | "CRITICAL_RISK";
  total_findings: number;
  critical_findings: number;
  high_findings: number;
  available_formats: string[];
}

export interface TopVulnerabilityReportDTO {
  id: string;
  title: string;
  severity: string;
  category: string;
  cve_id?: string;
  cwe_id?: string;
  cvss_score: number;
  epss_score: number;
  target_name?: string;
  created_at: string;
}

export interface ThreatAdvisoryDTO {
  severity: string;
  category: string;
  title: string;
  description: string;
  affected_target_url?: string;
}

export interface ExecutiveReportDataPayload {
  metadata: ExecutiveReportMetadataResponse;
  posture_summary: {
    composite_risk_score: number;
    posture_status: string;
    total_targets_count: number;
    total_open_findings: number;
    critical_findings_count: number;
    high_findings_count: number;
  };
  historical_trends: {
    organization_id: string;
    timeframe_days: number;
    current_risk_score: number;
    baseline_risk_score: number;
    risk_velocity: string;
    mean_time_to_remediate_hours: number;
    trend_points: Array<{
      date_str: string;
      composite_risk_score: number;
      open_findings_count: number;
      critical_findings_count: number;
    }>;
  };
  attack_surface_coverage: {
    organization_id: string;
    total_targets_count: number;
    assessed_targets_count: number;
    unassessed_targets_count: number;
    coverage_percentage: number;
    environments_breakdown: Array<{
      environment: string;
      target_count: number;
      risk_score: number;
    }>;
  };
  vulnerability_breakdown: {
    critical_count: number;
    high_count: number;
    medium_count: number;
    low_count: number;
    info_count: number;
  };
  top_findings: TopVulnerabilityReportDTO[];
  threat_advisories: ThreatAdvisoryDTO[];
  data_sources: string[];
}

export class ReportsService {
  private static readonly BASE_URL = "/api/v1/reports";

  /**
   * Generate an executive security posture report payload.
   */
  public static async generateExecutiveReport(
    req: CreateExecutiveReportRequest = {}
  ): Promise<ExecutiveReportDataPayload> {
    const res = await fetch(`${this.BASE_URL}/executive`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!res.ok) {
      throw new Error(`Failed to generate executive report: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Fetch metadata details for a specific report ID.
   */
  public static async getReportMetadata(
    reportId: string
  ): Promise<ExecutiveReportMetadataResponse> {
    const res = await fetch(`${this.BASE_URL}/${reportId}`);
    if (!res.ok) {
      throw new Error(`Failed to fetch report metadata: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Fetch rendered HTML content string for interactive preview.
   */
  public static async getHtmlReport(reportId: string): Promise<string> {
    const res = await fetch(`${this.BASE_URL}/${reportId}/html`);
    if (!res.ok) {
      throw new Error(`Failed to fetch HTML report: ${res.statusText}`);
    }
    return res.text();
  }

  /**
   * Trigger PDF download for executive report.
   */
  public static async downloadPdfReport(reportId: string): Promise<Blob> {
    const res = await fetch(`${this.BASE_URL}/${reportId}/pdf`);
    if (!res.ok) {
      throw new Error(`Failed to download PDF report: ${res.statusText}`);
    }
    return res.blob();
  }
}
