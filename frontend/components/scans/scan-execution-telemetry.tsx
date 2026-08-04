"use client";

import * as React from "react";
import { Server, Cpu, Clock, ShieldAlert, CheckCircle2 } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ProgressBar } from "@/components/ui/progress-bar";
import { ScanTelemetryResponse } from "@/services/scans.service";

export function ScanExecutionTelemetry({ telemetry }: { telemetry: ScanTelemetryResponse }) {
  return (
    <Card className="border-zinc-800 bg-zinc-950/80">
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <div className="flex items-center space-x-2">
          <Cpu className="h-5 w-5 text-red-500" />
          <CardTitle className="text-lg font-bold">Execution Telemetry Summary</CardTitle>
        </div>
        <Badge variant="critical" className="font-mono text-xs animate-pulse">
          {telemetry.status}
        </Badge>
      </CardHeader>

      <CardContent className="space-y-6">
        <ProgressBar value={telemetry.progress_percentage} colorVariant="crimson" />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="p-3.5 rounded-xl border border-zinc-800/80 bg-zinc-900/40 space-y-1">
            <span className="text-zinc-400">Target Name / Scope</span>
            <div className="font-bold text-zinc-100">{telemetry.target_name}</div>
            <div className="font-mono text-[10px] text-red-400 truncate">{telemetry.unmasked_target_url}</div>
          </div>

          <div className="p-3.5 rounded-xl border border-zinc-800/80 bg-zinc-900/40 space-y-1">
            <span className="text-zinc-400">Worker Node Attribution</span>
            <div className="font-mono text-zinc-100 font-bold">{telemetry.assigned_worker_node_id || "worker-01"}</div>
            <div className="text-[10px] text-emerald-400 font-mono">Sandbox UID 10001 (Read-Only Rootfs)</div>
          </div>

          <div className="p-3.5 rounded-xl border border-zinc-800/80 bg-zinc-900/40 space-y-1">
            <span className="text-zinc-400">Discovered Findings</span>
            <div className="text-xl font-bold font-mono text-red-400">{telemetry.findings_count} Findings</div>
            <div className="text-[10px] text-zinc-400">Duration: {telemetry.duration_seconds}s</div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
