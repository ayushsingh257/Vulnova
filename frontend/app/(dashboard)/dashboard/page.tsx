"use client";

import * as React from "react";
import { DashboardLayout } from "@/components/dashboard/dashboard-layout";
import { SecurityPostureCard } from "@/components/dashboard/security-posture-card";
import { ActiveScanMonitor } from "@/components/dashboard/active-scan-monitor";
import { VulnerabilityChart } from "@/components/dashboard/vulnerability-chart";
import { AssetRiskOverview } from "@/components/dashboard/asset-risk-overview";
import { SchedulesOverview } from "@/components/dashboard/schedules-overview";

export default function DashboardPage() {
  const [data, setData] = React.useState({
    posture_summary: {
      composite_risk_score: 78.5,
      posture_status: "ELEVATED_RISK",
      total_targets_count: 12,
      total_open_findings: 47,
      critical_findings_count: 3,
      high_findings_count: 14,
    },
    vulnerability_breakdown: {
      critical_count: 3,
      high_count: 14,
      medium_count: 20,
      low_count: 8,
      info_count: 2,
    },
    active_scans: [
      {
        job_id: "8d48aca2-c4b9-45b2-b42d-e6f2dbfdeb18",
        target_name: "Production API Gateway",
        target_url: "https://api.staging.example.com",
        execution_state: "ASSESSING",
        current_step: "Executing Active Security Plugins",
        started_at: new Date().toISOString(),
        running_duration_seconds: 145,
      },
    ],
    top_vulnerable_assets: [
      {
        target_id: "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        target_url: "https://auth.staging.example.com",
        environment: "PRODUCTION",
        risk_score: 92.0,
        critical_count: 2,
        high_count: 5,
      },
      {
        target_id: "7fa85f64-5717-4562-b3fc-2c963f66afa7",
        target_url: "https://api.staging.example.com",
        environment: "STAGING",
        risk_score: 74.5,
        critical_count: 1,
        high_count: 4,
      },
    ],
    schedules_summary: {
      total_active_schedules: 4,
      next_scheduled_run_at: new Date(Date.now() + 86400000).toISOString(),
    },
  });

  React.useEffect(() => {
    // Attempt fetching live data from API Gateway if available
    fetch("/api/v1/dashboard/overview")
      .then((res) => {
        if (res.ok) return res.json();
        return null;
      })
      .then((json) => {
        if (json) {
          setData(json);
        }
      })
      .catch(() => {
        // Fallback to client state
      });
  }, []);

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Top Hero Section: Security Posture Summary */}
        <SecurityPostureCard summary={data.posture_summary} />

        {/* Middle Grid: Active Scan Monitor & Vulnerability Distribution */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <ActiveScanMonitor scans={data.active_scans} />
          <VulnerabilityChart breakdown={data.vulnerability_breakdown} />
        </div>

        {/* Bottom Grid: Top Target Assets & Recurring Schedules */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <AssetRiskOverview assets={data.top_vulnerable_assets} />
          <SchedulesOverview summary={data.schedules_summary} />
        </div>
      </div>
    </DashboardLayout>
  );
}
