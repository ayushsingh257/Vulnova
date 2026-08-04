// Frontend Vulnerabilities API Service Abstraction Module.

export interface CVSSDetail {
  version: string;
  base_score: number;
  vector_string?: string;
  exploitability_score?: number;
  impact_score?: number;
}

export interface EPSSDetail {
  epss_score: number;
  percentile: number;
}

export interface VulnerabilityRiskContext {
  composite_risk_score: number;
  remediation_sla_hours: number;
  risk_level: string;
  affected_asset_count: number;
  exploitability_score?: number;
  impact_score?: number;
}

export interface ScanOrigin {
  job_id: string;
  target_name: string;
  target_environment: string;
  scan_profile: string;
  completed_at?: string;
}

export interface TriageHistoryItem {
  id: string;
  previous_status: string;
  new_status: string;
  actor_user_id?: string;
  comment?: string;
  risk_accepted_until?: string;
  created_at: string;
}

export interface AIExplanationSummary {
  id: string;
  summary: string;
  technical_details?: string;
  impact_analysis?: string;
  confidence_score: number;
  status: string;
}

export interface VulnerabilityIntelligenceResponse {
  id: string;
  organization_id: string;
  title: string;
  description: string;
  severity: string;
  category: string;
  cve_id?: string;
  cwe_id?: string;
  remediation?: string;
  cvss: CVSSDetail;
  epss: EPSSDetail;
  risk_context: VulnerabilityRiskContext;
  scan_origin: ScanOrigin;
  triage_status: string;
  triage_history: TriageHistoryItem[];
  ai_explanation?: AIExplanationSummary;
  created_at: string;
}

export interface EvidenceItem {
  id: string;
  finding_id: string;
  artifact_type: string;
  type_label: string;
  storage_path: string;
  metadata?: Record<string, any>;
  checksum: string;
  created_at: string;
}

export interface FindingEvidenceResponse {
  finding_id: string;
  evidence_items: EvidenceItem[];
  total_count: number;
}

export interface AttackPathNode {
  id: string;
  asset_name: string;
  asset_type: string;
  vulnerability_title: string;
  relationship: string;
  risk_impact: string;
  sequence_number: number;
}

export interface FindingAttackPathsResponse {
  finding_id: string;
  attack_path_id?: string;
  title: string;
  attack_summary: string;
  composite_risk_score: number;
  nodes: AttackPathNode[];
}

export interface RemediationStep {
  sequence_number: number;
  step_type: string;
  title: string;
  description: string;
  estimated_minutes: number;
}

export interface PatchSuggestion {
  file_path?: string;
  language: string;
  patch_code: string;
  explanation?: string;
}

export interface FindingRemediationResponse {
  finding_id: string;
  plan_id?: string;
  title: string;
  summary: string;
  explanation: string;
  verification_steps: string[];
  steps: RemediationStep[];
  patch_suggestions: PatchSuggestion[];
  ai_confidence_score: number;
}

export class VulnerabilitiesService {
  private static BASE_URL = "/api/v1/vulnerabilities";

  public static async getVulnerabilityDetails(
    findingId: string
  ): Promise<VulnerabilityIntelligenceResponse> {
    const res = await fetch(`${this.BASE_URL}/${findingId}`);
    if (!res.ok) {
      throw new Error(`Failed to fetch vulnerability details: ${res.statusText}`);
    }
    return res.json();
  }

  public static async getVulnerabilityEvidence(
    findingId: string
  ): Promise<FindingEvidenceResponse> {
    const res = await fetch(`${this.BASE_URL}/${findingId}/evidence`);
    if (!res.ok) {
      throw new Error(`Failed to fetch evidence artifacts: ${res.statusText}`);
    }
    return res.json();
  }

  public static async getVulnerabilityAttackPaths(
    findingId: string
  ): Promise<FindingAttackPathsResponse> {
    const res = await fetch(`${this.BASE_URL}/${findingId}/attack-path`);
    if (!res.ok) {
      throw new Error(`Failed to fetch attack path visualization: ${res.statusText}`);
    }
    return res.json();
  }

  public static async getVulnerabilityRemediation(
    findingId: string
  ): Promise<FindingRemediationResponse> {
    const res = await fetch(`${this.BASE_URL}/${findingId}/remediation`);
    if (!res.ok) {
      throw new Error(`Failed to fetch remediation guidance: ${res.statusText}`);
    }
    return res.json();
  }

  public static async requestAIRemediation(
    findingId: string
  ): Promise<FindingRemediationResponse> {
    const res = await fetch(`${this.BASE_URL}/${findingId}/remediation-ai`, {
      method: "POST",
    });
    if (!res.ok) {
      throw new Error(`Failed to generate AI remediation: ${res.statusText}`);
    }
    return res.json();
  }
}
