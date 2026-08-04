"use client";

import * as React from "react";
import { TrendingDown, TrendingUp, Minus, Activity, Clock } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export interface RiskTrendPoint {
  date_str: string;
  composite_risk_score: number;
  open_findings_count: number;
  critical_findings_count: number;
}

export interface HistoricalRiskChartProps {
  currentScore?: number;
  baselineScore?: number;
  riskVelocity?: "IMPROVING" | "DETERIORATING" | "STABLE" | string;
  mttrHours?: number;
  trendPoints?: RiskTrendPoint[];
}

export function HistoricalRiskChart({
  currentScore = 65.0,
  baselineScore = 78.0,
  riskVelocity = "IMPROVING",
  mttrHours = 32.5,
  trendPoints = [
    { date_str: "2026-07-05", composite_risk_score: 78.0, open_findings_count: 55, critical_findings_count: 5 },
    { date_str: "2026-07-12", composite_risk_score: 74.0, open_findings_count: 48, critical_findings_count: 4 },
    { date_str: "2026-07-19", composite_risk_score: 71.0, open_findings_count: 42, critical_findings_count: 3 },
    { date_str: "2026-07-26", composite_risk_score: 68.0, open_findings_count: 38, critical_findings_count: 2 },
    { date_str: "2026-08-04", composite_risk_score: 65.0, open_findings_count: 32, critical_findings_count: 1 },
  ],
}: HistoricalRiskChartProps) {
  const [timeframe, setTimeframe] = React.useState<"7d" | "30d" | "90d">("30d");

  const getVelocityBadge = (velocity: string) => {
    switch (velocity.toUpperCase()) {
      case "IMPROVING":
        return (
          <Badge variant="success" className="space-x-1 font-mono text-xs">
            <TrendingDown className="h-3.5 w-3.5" />
            <span>IMPROVING POSTURE</span>
          </Badge>
        );
      case "DETERIORATING":
        return (
          <Badge variant="critical" className="space-x-1 font-mono text-xs">
            <TrendingUp className="h-3.5 w-3.5" />
            <span>POSTURE DEGRADING</span>
          </Badge>
        );
      default:
        return (
          <Badge variant="info" className="space-x-1 font-mono text-xs">
            <Minus className="h-3.5 w-3.5" />
            <span>STABLE POSTURE</span>
          </Badge>
        );
    }
  };

  return (
    <Card className="border-zinc-800 bg-zinc-950/80">
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <div className="flex items-center space-x-2">
          <Activity className="h-5 w-5 text-red-500" />
          <CardTitle className="text-lg font-bold">Historical Risk Trajectory & Velocity</CardTitle>
        </div>

        <div className="flex items-center space-x-3">
          {getVelocityBadge(riskVelocity)}

          <div className="inline-flex rounded-lg border border-zinc-800 bg-zinc-900/60 p-0.5 text-xs font-mono">
            {(["7d", "30d", "90d"] as const).map((period) => (
              <button
                key={period}
                onClick={() => setTimeframe(period)}
                className={`px-2.5 py-1 rounded-md transition-colors ${
                  timeframe === period
                    ? "bg-zinc-800 text-white font-bold"
                    : "text-zinc-400 hover:text-zinc-200"
                }`}
              >
                {period}
              </button>
            ))}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-3.5 rounded-xl border border-zinc-800/80 bg-zinc-900/40">
            <span className="text-xs text-zinc-400">Current Risk Score</span>
            <div className="text-2xl font-extrabold text-white font-mono mt-1">{currentScore} / 100</div>
          </div>

          <div className="p-3.5 rounded-xl border border-zinc-800/80 bg-zinc-900/40">
            <span className="text-xs text-zinc-400">30-Day Baseline Score</span>
            <div className="text-2xl font-extrabold text-zinc-300 font-mono mt-1">{baselineScore} / 100</div>
          </div>

          <div className="p-3.5 rounded-xl border border-zinc-800/80 bg-zinc-900/40 flex items-center justify-between">
            <div>
              <span className="text-xs text-zinc-400">Mean Time to Remediate</span>
              <div className="text-2xl font-extrabold text-emerald-400 font-mono mt-1">{mttrHours}h</div>
            </div>
            <Clock className="h-8 w-8 text-emerald-500/30" />
          </div>
        </div>

        {/* Visual Trend Bar Visualization */}
        <div className="space-y-2 pt-2">
          <div className="flex items-center justify-between text-xs text-zinc-400 font-mono">
            <span>30-DAY RISK SNAPSHOT TIMELINE</span>
            <span>LOWER RISK SCORE = BETTER POSTURE</span>
          </div>

          <div className="grid grid-cols-5 gap-2 h-28 items-end p-3 rounded-xl border border-zinc-800/80 bg-zinc-900/40">
            {trendPoints.slice(-5).map((point, idx) => {
              const heightPct = Math.max(15, (point.composite_risk_score / 100) * 100);
              return (
                <div key={idx} className="flex flex-col items-center justify-end h-full space-y-1 group">
                  <span className="text-[10px] font-mono text-zinc-400 group-hover:text-white transition-colors">
                    {point.composite_risk_score}
                  </span>
                  <div
                    style={{ height: `${heightPct}%` }}
                    className="w-full rounded-md bg-gradient-to-t from-red-600/60 to-rose-500/80 group-hover:from-red-500 group-hover:to-rose-400 transition-all"
                  />
                  <span className="text-[9px] font-mono text-zinc-500 truncate w-full text-center">
                    {point.date_str.slice(5)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
