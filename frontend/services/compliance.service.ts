export interface ComplianceFindingMappingDTO {
  finding_id: string;
  title: string;
  severity: string;
  category: string;
  cwe_id?: string;
  cve_id?: string;
  status: string;
  asset_name?: string;
  evidence_checksum?: string;
  remediation_summary?: string;
}

export interface ComplianceControlDTO {
  control_id: string;
  title: string;
  description: string;
  status: "PASS" | "FAIL" | string;
  mapped_findings_count: number;
  affected_findings: ComplianceFindingMappingDTO[];
  remediation_guidance: string;
}

export interface ComplianceScoreResponse {
  framework_id: string;
  framework_name: string;
  framework_version: string;
  total_controls: number;
  passed_controls: number;
  failed_controls: number;
  compliance_percentage: number;
}

export interface ComplianceOverviewResponse {
  framework_id: string;
  framework_name: string;
  framework_version: string;
  score: ComplianceScoreResponse;
  controls: ComplianceControlDTO[];
  failed_controls: ComplianceControlDTO[];
  top_remediation_priorities: Array<{
    control_id: string;
    title: string;
    affected_findings_count: number;
    remediation_guidance: string;
  }>;
}

export class ComplianceService {
  private static readonly BASE_URL = "/api/v1/compliance";

  /**
   * Fetch compliance posture overview for a specific framework.
   */
  public static async getComplianceOverview(
    framework: string
  ): Promise<ComplianceOverviewResponse> {
    const res = await fetch(`${this.BASE_URL}/${framework}/overview`);
    if (!res.ok) {
      throw new Error(`Failed to fetch compliance overview: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Fetch all controls mapped with finding evidence for a framework.
   */
  public static async getComplianceControls(
    framework: string
  ): Promise<ComplianceControlDTO[]> {
    const res = await fetch(`${this.BASE_URL}/${framework}/controls`);
    if (!res.ok) {
      throw new Error(`Failed to fetch compliance controls: ${res.statusText}`);
    }
    return res.json();
  }

  /**
   * Download compliance report JSON payload.
   */
  public static async exportComplianceReport(framework: string): Promise<void> {
    const res = await fetch(`${this.BASE_URL}/${framework}/export`);
    if (!res.ok) {
      throw new Error(`Failed to export compliance report: ${res.statusText}`);
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `Vulnova_Compliance_${framework}.json`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  }
}
