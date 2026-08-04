"use client";

import * as React from "react";
import { Radio, Play, CheckCircle2, AlertOctagon, Cpu, RefreshCw } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ProgressBar } from "@/components/ui/progress-bar";

export interface ActiveScanJob {
  job_id: string;
  target_name: string;
  target_url: string;
  execution_state: "QUEUED" | "CRAWLING" | "ASSESSING" | "AI_ANALYSIS" | "COMPLETED" | "FAILED" | string;
  current_step?: string;
  started_at?: string;
  running_duration_seconds?: number;
}

export function ActiveScanMonitor({ scans }: { scans: ActiveScanJob[] }) {
  const getStepProgress = (state: string) => {
    switch (state) {
      case "QUEUED":
        return 10;
      case "CRAWLING":
        return 35;
      case "ASSESSING":
        return 65;
      case "AI_ANALYSIS":
        return 90;
      case "COMPLETED":
        return 100;
      default:
        return 50;
    }
  };

  const getStateBadge = (state: string) => {
    switch (state) {
      case "CRAWLING":
        return <Badge variant="info">CRAWLING TARGET</Badge>;
      case "ASSESSING":
        return <Badge variant="warning">EXECUTING PLUGINS</Badge>;
      case "AI_ANALYSIS":
        return <Badge variant="default">AI REASONING</Badge>;
      case "COMPLETED":
        return <Badge variant="success">COMPLETED</Badge>;
      case "FAILED":
        return <Badge variant="critical">FAILED</Badge>;
      default:
        return <Badge variant="default">QUEUED</Badge>;
    }
  };

  return (
    <Card className="border-zinc-800 bg-zinc-950/80">
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <div className="flex items-center space-x-2">
          <Radio className="h-5 w-5 text-red-500 animate-pulse" />
          <CardTitle className="text-lg font-bold">Active Scan Telemetry Monitor</CardTitle>
        </div>
        <span className="text-xs text-zinc-400 font-mono">
          {scans.length} Active Executions
        </span>
      </CardHeader>

      <CardContent className="space-y-4">
        {scans.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-8 rounded-lg border border-dashed border-zinc-800 text-center">
            <CheckCircle2 className="h-8 w-8 text-emerald-500 mb-2" />
            <p className="text-sm font-semibold text-zinc-300">No Scans Currently Running</p>
            <p className="text-xs text-zinc-500 mt-1">All scheduled and manual security scans have completed.</p>
          </div>
        ) : (
          scans.map((scan) => (
            <div
              key={scan.job_id}
              className="p-4 rounded-xl border border-zinc-800/80 bg-zinc-900/40 space-y-3 transition-all hover:border-zinc-700"
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm font-bold text-zinc-100 flex items-center space-x-2">
                    <span>{scan.target_name}</span>
                    <span className="text-xs text-zinc-500 font-mono">({scan.target_url})</span>
                  </div>
                  <div className="text-xs text-zinc-400 mt-0.5 flex items-center space-x-1.5">
                    <Cpu className="h-3.5 w-3.5 text-red-400" />
                    <span>{scan.current_step || scan.execution_state}</span>
                  </div>
                </div>
                {getStateBadge(scan.execution_state)}
              </div>

              <div className="space-y-1.5">
                <div className="flex justify-between text-[11px] font-mono text-zinc-400">
                  <span>Step Progress</span>
                  <span>{getStepProgress(scan.execution_state)}%</span>
                </div>
                <ProgressBar value={getStepProgress(scan.execution_state)} colorVariant="crimson" />
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
