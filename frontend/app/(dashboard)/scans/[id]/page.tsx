"use client";

import * as React from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Cpu, Radio, ShieldAlert } from "lucide-react";
import { DashboardLayout } from "@/components/dashboard/dashboard-layout";
import { ScanExecutionTelemetry } from "@/components/scans/scan-execution-telemetry";
import { ScanActivityTimeline } from "@/components/scans/scan-activity-timeline";
import { LiveEventConsole } from "@/components/scans/live-event-console";
import { ScanControlsBar } from "@/components/scans/scan-controls-bar";
import { ScansService, ScanTelemetryResponse } from "@/services/scans.service";

export default function ScanDetailPage() {
  const params = useParams();
  const scanId = (params?.id as string) || "8d48aca2-c4b9-45b2-b42d-e6f2dbfdeb18";

  const [telemetry, setTelemetry] = React.useState<ScanTelemetryResponse>({
    id: scanId,
    target_name: "Production API Gateway Scope",
    environment: "PRODUCTION",
    unmasked_target_url: "https://api.staging.example.com",
    profile_name: "FULL_RECON",
    status: "ASSESSING",
    current_step: "Executing Active Security Assessment Plugins",
    progress_percentage: 65.0,
    findings_count: 4,
    started_at: new Date().toISOString(),
    duration_seconds: 145,
    assigned_worker_node_id: "worker-node-01",
    timeline_items: [
      {
        timestamp: "10:01:12 UTC",
        stage: "QUEUED",
        title: "Job Dispatched & Priority Queued",
        description: "Task assigned to Celery worker queue (scans.default) and verified against CFAA consent contract.",
        status: "COMPLETED",
      },
      {
        timestamp: "10:02:45 UTC",
        stage: "PROBING",
        title: "Target Scope Verification Probes",
        description: "DNS resolution, SSL handshake, and host availability checks completed successfully.",
        status: "COMPLETED",
      },
      {
        timestamp: "10:04:30 UTC",
        stage: "CRAWLING",
        title: "Attack Surface Crawling",
        description: "Discovered 42 REST API endpoints and input parameters.",
        status: "COMPLETED",
      },
      {
        timestamp: "10:08:15 UTC",
        stage: "ASSESSING",
        title: "Dynamic Plugin Assessment",
        description: "Executing active DAST payload probes (SQLi, XSS, SSRF, RCE).",
        status: "IN_PROGRESS",
      },
    ],
  });

  const loadTelemetry = React.useCallback(() => {
    ScansService.getScanTelemetry(scanId)
      .then((res) => res && setTelemetry(res))
      .catch(() => {});
  }, [scanId]);

  React.useEffect(() => {
    loadTelemetry();
  }, [loadTelemetry]);

  return (
    <DashboardLayout>
      <div className="space-y-6">
        {/* Top Navigation & Controls Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-zinc-800/80 pb-4">
          <div className="flex items-center space-x-3">
            <Link
              href="/scans"
              className="p-2 rounded-lg border border-zinc-800 bg-zinc-900 text-zinc-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
            </Link>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-xl font-bold text-white tracking-tight">{telemetry.target_name}</h1>
                <span className="text-xs font-mono text-red-400">({telemetry.unmasked_target_url})</span>
              </div>
              <p className="text-xs text-zinc-400">
                Live WebSocket Telemetry Stream • Scan ID: <span className="font-mono">{scanId}</span>
              </p>
            </div>
          </div>

          <ScanControlsBar scanId={scanId} status={telemetry.status} onActionCompleted={loadTelemetry} />
        </div>

        {/* Telemetry Summary Card */}
        <ScanExecutionTelemetry telemetry={telemetry} />

        {/* Activity Timeline & Real-Time Event Log Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <ScanActivityTimeline items={telemetry.timeline_items} />
          <LiveEventConsole />
        </div>
      </div>
    </DashboardLayout>
  );
}
