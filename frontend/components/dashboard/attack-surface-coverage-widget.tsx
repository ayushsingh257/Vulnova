"use client";

import * as React from "react";
import { Server, ShieldCheck, AlertCircle } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { ProgressBar } from "@/components/ui/progress-bar";

export interface EnvironmentBreakdown {
  environment: string;
  target_count: number;
  risk_score: number;
}

export interface AttackSurfaceCoverageProps {
  totalTargets?: number;
  assessedTargets?: number;
  unassessedTargets?: number;
  coveragePercentage?: number;
  environments?: EnvironmentBreakdown[];
}

export function AttackSurfaceCoverageWidget({
  totalTargets = 12,
  assessedTargets = 10,
  unassessedTargets = 2,
  coveragePercentage = 83.3,
  environments = [
    { environment: "PRODUCTION", target_count: 5, risk_score: 75.0 },
    { environment: "STAGING", target_count: 4, risk_score: 45.0 },
    { environment: "DEVELOPMENT", target_count: 3, risk_score: 20.0 },
  ],
}: AttackSurfaceCoverageProps) {
  return (
    <Card className="border-zinc-800 bg-zinc-950/80">
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <div className="flex items-center space-x-2">
          <Server className="h-5 w-5 text-red-500" />
          <CardTitle className="text-lg font-bold">Attack Surface Coverage Topology</CardTitle>
        </div>
        <span className="text-xs text-zinc-400 font-mono">
          Asset Assessment Coverage: <strong className="text-white">{coveragePercentage}%</strong>
        </span>
      </CardHeader>

      <CardContent className="space-y-6">
        <ProgressBar value={coveragePercentage} colorVariant="emerald" />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          {environments.map((env, idx) => (
            <div
              key={idx}
              className="p-3.5 rounded-xl border border-zinc-800/80 bg-zinc-900/40 space-y-2 hover:border-zinc-700 transition-all"
            >
              <div className="flex items-center justify-between font-mono font-bold">
                <span className="text-zinc-200">{env.environment}</span>
                <span className="text-red-400">{env.target_count} Targets</span>
              </div>
              <div className="flex items-center justify-between text-zinc-400 text-[11px]">
                <span>Risk Level</span>
                <span className="font-mono">{env.risk_score} / 100</span>
              </div>
            </div>
          ))}
        </div>

        <div className="p-3 rounded-lg border border-zinc-800 bg-zinc-900/30 flex items-center justify-between text-xs">
          <div className="flex items-center space-x-2 text-zinc-300">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            <span>Assessed Active Scope: <strong>{assessedTargets}</strong> targets</span>
          </div>
          {unassessedTargets > 0 && (
            <div className="flex items-center space-x-1.5 text-amber-400 font-mono text-[11px]">
              <AlertCircle className="h-3.5 w-3.5" />
              <span>{unassessedTargets} Unassessed Assets</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
