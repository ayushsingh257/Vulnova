"use client";

import React from "react";
import { ShieldCheck, ShieldAlert, Award } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ComplianceScoreResponse } from "@/services/compliance.service";

interface ComplianceScoreCardProps {
  score: ComplianceScoreResponse;
  title?: string;
  subtitle?: string;
}

export const ComplianceScoreCard: React.FC<ComplianceScoreCardProps> = ({
  score,
  title,
  subtitle,
}) => {
  const pct = score.compliance_percentage;
  const isHigh = pct >= 80;
  const isMedium = pct >= 60 && pct < 80;

  const scoreColorClass = isHigh
    ? "text-emerald-400 border-emerald-500/40 bg-emerald-950/20"
    : isMedium
    ? "text-amber-400 border-amber-500/40 bg-amber-950/20"
    : "text-red-400 border-red-500/40 bg-red-950/20";

  const badgeVariant = isHigh ? "success" : isMedium ? "warning" : "critical";

  return (
    <Card className="border-zinc-800 bg-zinc-950/80 backdrop-blur-md">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div>
          <CardTitle className="text-lg font-bold text-zinc-100">
            {title || score.framework_name}
          </CardTitle>
          <p className="text-xs text-zinc-400 mt-1">
            {subtitle || `Version: ${score.framework_version}`}
          </p>
        </div>
        <Badge variant={badgeVariant}>
          {isHigh ? "COMPLIANT" : isMedium ? "NEEDS ATTENTION" : "NON-COMPLIANT"}
        </Badge>
      </CardHeader>
      <CardContent className="pt-4 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div
              className={`flex h-16 w-16 items-center justify-center rounded-2xl border ${scoreColorClass} shadow-xl`}
            >
              {isHigh ? (
                <ShieldCheck className="h-8 w-8 text-emerald-400" />
              ) : isMedium ? (
                <Award className="h-8 w-8 text-amber-400" />
              ) : (
                <ShieldAlert className="h-8 w-8 text-red-400" />
              )}
            </div>
            <div>
              <div className="text-3xl font-extrabold text-white tracking-tight">
                {score.compliance_percentage}%
              </div>
              <div className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                Compliance Posture Score
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-6 text-right">
            <div>
              <div className="text-xl font-bold text-emerald-400">
                {score.passed_controls}
              </div>
              <div className="text-[11px] font-medium text-zinc-500 uppercase">
                Passed Controls
              </div>
            </div>
            <div className="border-l border-zinc-800 pl-6">
              <div className="text-xl font-bold text-red-400">
                {score.failed_controls}
              </div>
              <div className="text-[11px] font-medium text-zinc-500 uppercase">
                Failed Controls
              </div>
            </div>
            <div className="border-l border-zinc-800 pl-6">
              <div className="text-xl font-bold text-zinc-200">
                {score.total_controls}
              </div>
              <div className="text-[11px] font-medium text-zinc-500 uppercase">
                Total Controls
              </div>
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-zinc-900 h-2.5 rounded-full overflow-hidden border border-zinc-800">
          <div
            className={`h-full transition-all duration-500 ${
              isHigh ? "bg-emerald-500" : isMedium ? "bg-amber-500" : "bg-red-500"
            }`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </CardContent>
    </Card>
  );
};
