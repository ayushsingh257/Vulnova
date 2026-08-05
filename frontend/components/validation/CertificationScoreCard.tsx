"use client";

import React from "react";
import { Award, AlertTriangle, XCircle, CheckCircle2 } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface CertificationScoreCardProps {
  certificationScore: number;
  overallStatus: string;
  passedCount: number;
  failedCount: number;
  warningCount: number;
  executedAt?: string;
}

export const CertificationScoreCard: React.FC<CertificationScoreCardProps> = ({
  certificationScore,
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
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-600/20 border border-amber-500/40 text-amber-400">
            <Award className="h-5 w-5" />
          </div>
          <div>
            <CardTitle className="text-base font-bold text-white">
              Security Control Plane Final Certification Score
            </CardTitle>
            <p className="text-xs text-zinc-400 mt-0.5">
              Comprehensive Era 10 enterprise security compliance & production readiness certification matrix
            </p>
          </div>
        </div>

        <Badge variant={getBadgeVariant(overallStatus)} className="text-xs font-bold">
          {overallStatus === "PASSED" ? "ENTERPRISE CERTIFIED" : overallStatus}
        </Badge>
      </CardHeader>

      <CardContent className="pt-6 grid grid-cols-1 md:grid-cols-4 gap-6 text-center">
        {/* Certification Score Gauge */}
        <div className="flex flex-col items-center justify-center border-r border-zinc-800/80 pr-4">
          <span className="text-4xl font-black tracking-tight text-amber-400">
            {certificationScore}%
          </span>
          <span className="text-xs font-semibold text-zinc-400 mt-1">
            Compliance Score
          </span>
        </div>

        {/* Passed */}
        <div className="flex flex-col items-center justify-center border-r border-zinc-800/80 pr-4">
          <div className="flex items-center space-x-1.5 text-emerald-400 mb-1">
            <CheckCircle2 className="h-4 w-4" />
            <span className="text-2xl font-bold">{passedCount} / 10</span>
          </div>
          <span className="text-xs text-zinc-400">Control Domains Certified</span>
        </div>

        {/* Warnings */}
        <div className="flex flex-col items-center justify-center border-r border-zinc-800/80 pr-4">
          <div className="flex items-center space-x-1.5 text-amber-400 mb-1">
            <AlertTriangle className="h-4 w-4" />
            <span className="text-2xl font-bold">{warningCount}</span>
          </div>
          <span className="text-xs text-zinc-400">Compliance Warnings</span>
        </div>

        {/* Failed */}
        <div className="flex flex-col items-center justify-center">
          <div className="flex items-center space-x-1.5 text-red-400 mb-1">
            <XCircle className="h-4 w-4" />
            <span className="text-2xl font-bold">{failedCount}</span>
          </div>
          <span className="text-xs text-zinc-400">Certification Blockers</span>
        </div>
      </CardContent>
    </Card>
  );
};
