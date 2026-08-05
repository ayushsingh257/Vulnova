"use client";

import React from "react";
import { Shield, AlertTriangle, Activity, Target } from "lucide-react";
import { ExecutiveReportMetadataResponse } from "@/services/reports.service";

interface SecurityMetricsSummaryProps {
  metadata: ExecutiveReportMetadataResponse;
  mttrHours?: number;
}

export function SecurityMetricsSummary({
  metadata,
  mttrHours = 18.5,
}: SecurityMetricsSummaryProps) {
  const isSecure = metadata.posture_status === "SECURE";
  const isElevated = metadata.posture_status === "ELEVATED_RISK";

  return (
    <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      {/* Composite Posture Score */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
        <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
          <span>Posture Score</span>
          <Shield className="w-4 h-4 text-sky-400" />
        </div>
        <div className="mt-3 flex items-baseline justify-between">
          <span className="text-3xl font-extrabold text-sky-400">
            {metadata.posture_score.toFixed(1)}
          </span>
          <span
            className={`text-xs px-2 py-0.5 rounded-full font-bold uppercase ${
              isSecure
                ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                : isElevated
                ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                : "bg-red-500/20 text-red-400 border border-red-500/30"
            }`}
          >
            {metadata.posture_status.replace("_", " ")}
          </span>
        </div>
      </div>

      {/* Critical Findings */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
        <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
          <span>Critical Severity</span>
          <AlertTriangle className="w-4 h-4 text-rose-500" />
        </div>
        <div className="mt-3 flex items-baseline justify-between">
          <span className="text-3xl font-extrabold text-rose-500">
            {metadata.critical_findings}
          </span>
          <span className="text-xs text-slate-500">
            {metadata.high_findings} High
          </span>
        </div>
      </div>

      {/* Total Open Findings */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
        <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
          <span>Open Findings</span>
          <Target className="w-4 h-4 text-sky-400" />
        </div>
        <div className="mt-3 flex items-baseline justify-between">
          <span className="text-3xl font-extrabold text-slate-100">
            {metadata.total_findings}
          </span>
          <span className="text-xs text-slate-500">In Active Scope</span>
        </div>
      </div>

      {/* MTTR */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
        <div className="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
          <span>MTTR Trajectory</span>
          <Activity className="w-4 h-4 text-emerald-400" />
        </div>
        <div className="mt-3 flex items-baseline justify-between">
          <span className="text-3xl font-extrabold text-emerald-400">
            {mttrHours.toFixed(1)}h
          </span>
          <span className="text-xs text-slate-500">Mean Time to Fix</span>
        </div>
      </div>
    </div>
  );
}
