"use client";

import * as React from "react";
import Link from "next/link";
import { Play, Eye, ExternalLink, ShieldAlert, AlertCircle, CheckCircle2, Clock } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ProgressBar } from "@/components/ui/progress-bar";
import { ScanJobItem } from "@/services/scans.service";

export function ScanListTable({
  scans = [],
  onSelectScan,
}: {
  scans: ScanJobItem[];
  onSelectScan?: (scanId: string) => void;
}) {
  const getStatusBadge = (status: string) => {
    switch (status.toUpperCase()) {
      case "COMPLETED":
        return (
          <Badge variant="success" className="font-mono text-[10px]">
            COMPLETED
          </Badge>
        );
      case "ASSESSING":
      case "CRAWLING":
      case "PROBING":
        return (
          <Badge variant="critical" className="font-mono text-[10px] animate-pulse">
            RUNNING
          </Badge>
        );
      case "FAILED":
        return (
          <Badge variant="warning" className="font-mono text-[10px]">
            FAILED
          </Badge>
        );
      default:
        return (
          <Badge variant="info" className="font-mono text-[10px]">
            QUEUED
          </Badge>
        );
    }
  };

  return (
    <Card className="border-zinc-800 bg-zinc-950/80">
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <div className="flex items-center space-x-2">
          <ShieldAlert className="h-5 w-5 text-red-500" />
          <CardTitle className="text-lg font-bold">Assessment Execution Registry</CardTitle>
        </div>
        <span className="text-xs text-zinc-400 font-mono">
          Total Jobs: <strong className="text-white">{scans.length}</strong>
        </span>
      </CardHeader>

      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-zinc-800 bg-zinc-900/40 text-[11px] font-mono uppercase text-zinc-400">
              <tr>
                <th className="p-3">Target Scope</th>
                <th className="p-3">Profile</th>
                <th className="p-3">Execution State</th>
                <th className="p-3">Progress</th>
                <th className="p-3">Findings</th>
                <th className="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800/60">
              {scans.map((scan) => (
                <tr key={scan.id} className="hover:bg-zinc-900/30 transition-colors">
                  <td className="p-3 space-y-0.5">
                    <div className="font-bold text-zinc-200">{scan.target_name}</div>
                    <div className="font-mono text-[10px] text-zinc-500">{scan.masked_target_url}</div>
                  </td>
                  <td className="p-3">
                    <Badge variant="info" className="font-mono text-[10px]">
                      {scan.profile_name}
                    </Badge>
                  </td>
                  <td className="p-3 space-y-1">
                    {getStatusBadge(scan.status)}
                    <div className="text-[10px] text-zinc-400 truncate max-w-[180px]">
                      {scan.current_step}
                    </div>
                  </td>
                  <td className="p-3 w-32">
                    <div className="space-y-1">
                      <ProgressBar value={scan.progress_percentage} colorVariant="crimson" />
                      <div className="text-[10px] font-mono text-zinc-400 text-right">
                        {scan.progress_percentage}%
                      </div>
                    </div>
                  </td>
                  <td className="p-3">
                    <span
                      className={`font-mono font-bold ${
                        scan.findings_count > 0 ? "text-red-400" : "text-emerald-400"
                      }`}
                    >
                      {scan.findings_count}
                    </span>
                  </td>
                  <td className="p-3 text-right">
                    <Link
                      href={`/scans/${scan.id}`}
                      className="inline-flex items-center space-x-1 text-xs font-mono text-red-400 hover:text-red-300 transition-colors"
                    >
                      <span>Telemetry</span>
                      <ExternalLink className="h-3 w-3" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
