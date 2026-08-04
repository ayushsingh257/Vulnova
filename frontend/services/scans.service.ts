// Frontend Scans API & WebSocket Stream Service Abstraction Module.

export interface ScanJobItem {
  id: string;
  target_name: string;
  environment: string;
  masked_target_url: string;
  profile_name: string;
  status: string;
  current_step: string;
  progress_percentage: number;
  findings_count: number;
  started_at: string;
  completed_at?: string;
}

export interface PaginatedScansResponse {
  items: ScanJobItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface TimelineItem {
  timestamp: string;
  stage: string;
  title: string;
  description: string;
  status: string;
}

export interface ScanTelemetryResponse {
  id: string;
  target_name: string;
  environment: string;
  unmasked_target_url: string;
  profile_name: string;
  status: string;
  current_step: string;
  progress_percentage: number;
  findings_count: number;
  started_at: string;
  completed_at?: string;
  duration_seconds: number;
  assigned_worker_node_id?: string;
  timeline_items: TimelineItem[];
}

export interface DispatchScanRequest {
  target_id: string;
  scan_profile: string;
  priority_queue?: string;
  legal_consent_confirmed: boolean;
}

export class ScansService {
  private static BASE_URL = "/api/v1/assessments";

  public static async listScans(
    page: number = 1,
    pageSize: number = 20,
    statusFilter?: string,
    search?: string
  ): Promise<PaginatedScansResponse> {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
    });
    if (statusFilter) params.append("status_filter", statusFilter);
    if (search) params.append("search", search);

    const res = await fetch(`${this.BASE_URL}?${params.toString()}`);
    if (!res.ok) {
      throw new Error(`Failed to fetch scan jobs: ${res.statusText}`);
    }
    return res.json();
  }

  public static async getScanTelemetry(
    scanId: string
  ): Promise<ScanTelemetryResponse> {
    const res = await fetch(`${this.BASE_URL}/${scanId}/telemetry`);
    if (!res.ok) {
      throw new Error(`Failed to fetch scan telemetry: ${res.statusText}`);
    }
    return res.json();
  }

  public static async dispatchScan(
    payload: DispatchScanRequest
  ): Promise<{ id: string }> {
    const res = await fetch(this.BASE_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      throw new Error(`Failed to dispatch scan job: ${res.statusText}`);
    }
    return res.json();
  }

  public static async pauseScan(scanId: string): Promise<void> {
    await fetch(`${this.BASE_URL}/${scanId}/pause`, { method: "POST" });
  }

  public static async resumeScan(scanId: string): Promise<void> {
    await fetch(`${this.BASE_URL}/${scanId}/resume`, { method: "POST" });
  }

  public static async cancelScan(scanId: string): Promise<void> {
    await fetch(`${this.BASE_URL}/${scanId}/cancel`, { method: "POST" });
  }

  public static async retryScan(scanId: string): Promise<void> {
    await fetch(`${this.BASE_URL}/${scanId}/retry`, { method: "POST" });
  }
}
