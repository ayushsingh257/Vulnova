"use client";

import * as React from "react";
import { ShieldAlert, ShieldCheck, Activity, Target, AlertTriangle } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export interface SecurityPostureSummary {
  composite_risk_score: number;
  posture_status: "SECURE" | "ELEVATED_RISK" | "CRITICAL_RISK" | string;
  total_targets_count: number;
  total_open_findings: number;
  critical_findings_count: number;
  high_findings_count: number;
}

export function SecurityPostureCard({ summary }: { summary: SecurityPostureSummary }) {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case "CRITICAL_RISK":
        return <Badge variant="critical">CRITICAL RISK</Badge>;
      case "ELEVATED_RISK":
        return <Badge variant="warning">ELEVATED RISK</Badge>;
      default:
        return <Badge variant="success">SECURE</Badge>;
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 75) return "text-red-500 border-red-500/30 bg-red-950/20";
    if (score >= 40) return "text-amber-400 border-amber-500/30 bg-amber-950/20";
    return "text-emerald-400 border-emerald-500/30 bg-emerald-950/20";
  };

  return (
    <Card className="relative overflow-hidden border-zinc-800 bg-gradient-to-br from-zinc-950 via-zinc-900/60 to-zinc-950">
      <div className="absolute top-0 right-0 h-48 w-48 rounded-full bg-red-600/5 blur-3xl pointer-events-none" />

      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-6">
        <div>
          <CardTitle className="text-xl font-bold flex items-center space-x-2">
            <Activity className="h-5 w-5 text-red-500" />
            <span>Organizational Security Posture</span>
          </CardTitle>
          <p className="text-xs text-zinc-400 mt-1">
            Real-time multi-source threat & vulnerability posture summary
          </p>
        </div>
        {getStatusBadge(summary.posture_status)}
      </CardHeader>

      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 items-center">
          {/* Composite Risk Score Gauge */}
          <div className="flex flex-col items-center justify-center p-4 rounded-xl border border-zinc-800 bg-zinc-900/40">
            <div
              className={`flex h-24 w-24 flex-col items-center justify-center rounded-full border-4 shadow-xl font-mono ${getScoreColor(
                summary.composite_risk_score
              )}`}
            >
              <span className="text-3xl font-extrabold tracking-tight">
                {summary.composite_risk_score.toFixed(1)}
              </span>
              <span className="text-[10px] font-semibold uppercase tracking-widest text-zinc-400">
                RISK SCORE
              </span>
            </div>
            <span className="text-[11px] text-zinc-400 mt-2">Weighted Threat Score</span>
          </div>

          {/* Metric Columns */}
          <div className="flex items-center space-x-4 p-4 rounded-xl border border-zinc-800/80 bg-zinc-900/30">
            <div className="p-3 rounded-lg bg-blue-950/50 text-blue-400 border border-blue-800/40">
              <Target className="h-6 w-6" />
            </div>
            <div>
              <div className="text-2xl font-bold text-zinc-100">{summary.total_targets_count}</div>
              <div className="text-xs text-zinc-400">Active Target Assets</div>
            </div>
          </div>

          <div className="flex items-center space-x-4 p-4 rounded-xl border border-zinc-800/80 bg-zinc-900/30">
            <div className="p-3 rounded-lg bg-red-950/50 text-red-400 border border-red-800/40">
              <ShieldAlert className="h-6 w-6" />
            </div>
            <div>
              <div className="text-2xl font-bold text-red-400">{summary.critical_findings_count}</div>
              <div className="text-xs text-zinc-400">Critical Vulnerabilities</div>
            </div>
          </div>

          <div className="flex items-center space-x-4 p-4 rounded-xl border border-zinc-800/80 bg-zinc-900/30">
            <div className="p-3 rounded-lg bg-orange-950/50 text-orange-400 border border-orange-800/40">
              <AlertTriangle className="h-6 w-6" />
            </div>
            <div>
              <div className="text-2xl font-bold text-orange-400">{summary.high_findings_count}</div>
              <div className="text-xs text-zinc-400">High Vulnerabilities</div>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
