"use client";

import React from "react";
import { ShieldCheck, AlertTriangle, XCircle, CheckCircle2 } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface InfrastructurePassRateCardProps {
  passRate: number;
  overallStatus: string;
  passedCount: number;
  failedCount: number;
  warningCount: number;
  executedAt?: string;
}

export const InfrastructurePassRateCard: React.FC<InfrastructurePassRateCardProps> = ({
  passRate,
  overallStatus,
  passedCount,
  failedCount,
  warningCount,
  executedAt,
}) => {
  const getBadgeVariant = (status: string) => {
    switch (status.toUpperCase()) {
      case "PASSED":
        return "success";
      case "DEGRADED":
        return "warning";
      default:
        return "critical";
    }
  };

  return (
    <Card className="border-zinc-800 bg-zinc-950/80 backdrop-blur-md">
      <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-zinc-800">
        <div className="flex items-center space-x-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-600/20 border border-emerald-500/40 text-emerald-400">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <CardTitle className="text-base font-bold text-white">
              Infrastructure & Configuration Posture
            </CardTitle>
            <p className="text-xs text-zinc-400 mt-0.5">
              Automated deployment, container, cloud & operational security assertion score
            </p>
          </div>
        </div>

        <Badge variant={getBadgeVariant(overallStatus)} className="text-xs font-bold">
          {overallStatus}
        </Badge>
      </CardHeader>

      <CardContent className="pt-6 grid grid-cols-1 md:grid-cols-4 gap-6 text-center">
        {/* Pass Rate Gauge */}
        <div className="flex flex-col items-center justify-center border-r border-zinc-800/80 pr-4">
          <span className="text-4xl font-black tracking-tight text-white">
            {passRate}%
          </span>
          <span className="text-xs font-semibold text-zinc-400 mt-1">
            Infrastructure Score
          </span>
        </div>

        {/* Passed */}
        <div className="flex flex-col items-center justify-center border-r border-zinc-800/80 pr-4">
          <div className="flex items-center space-x-1.5 text-emerald-400 mb-1">
            <CheckCircle2 className="h-4 w-4" />
            <span className="text-2xl font-bold">{passedCount} / 10</span>
          </div>
          <span className="text-xs text-zinc-400">Controls Verified Passed</span>
        </div>

        {/* Warnings */}
        <div className="flex flex-col items-center justify-center border-r border-zinc-800/80 pr-4">
          <div className="flex items-center space-x-1.5 text-amber-400 mb-1">
            <AlertTriangle className="h-4 w-4" />
            <span className="text-2xl font-bold">{warningCount}</span>
          </div>
          <span className="text-xs text-zinc-400">Warnings Discovered</span>
        </div>

        {/* Failed */}
        <div className="flex flex-col items-center justify-center">
          <div className="flex items-center space-x-1.5 text-red-400 mb-1">
            <XCircle className="h-4 w-4" />
            <span className="text-2xl font-bold">{failedCount}</span>
          </div>
          <span className="text-xs text-zinc-400">Infrastructure Violations</span>
        </div>
      </CardContent>
    </Card>
  );
};
