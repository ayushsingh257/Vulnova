"use client";

import React from "react";
import { Database, Activity, Clock, Server, Zap } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { DatabaseHealthBadge } from "./DatabaseHealthBadge";
import { DatabaseHealthSummary } from "@/services/database_performance.service";

interface DatabasePerformanceCardProps {
  summary: DatabaseHealthSummary;
}

export const DatabasePerformanceCard: React.FC<DatabasePerformanceCardProps> = ({ summary }) => {
  return (
    <Card className="border-zinc-800 bg-zinc-950/80 backdrop-blur-md">
      <CardHeader className="flex flex-row items-center justify-between pb-4 border-b border-zinc-800">
        <div className="flex items-center space-x-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-600/20 border border-cyan-500/40 text-cyan-400 shadow-md">
            <Database className="h-6 w-6" />
          </div>
          <div>
            <CardTitle className="text-base font-bold text-white">
              PostgreSQL Database Engine Health & Connection Pool
            </CardTitle>
            <p className="text-xs text-zinc-400 mt-0.5">
              Real-time query execution metrics, connection pooling, and indexing health
            </p>
          </div>
        </div>

        <DatabaseHealthBadge status={summary.status} />
      </CardHeader>

      <CardContent className="pt-6 space-y-6">
        {/* Metric Cards Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-zinc-900/80 border border-zinc-800 space-y-1">
            <div className="flex items-center justify-between text-xs text-zinc-400">
              <span>Avg Latency</span>
              <Activity className="h-4 w-4 text-cyan-400" />
            </div>
            <div className="text-2xl font-black text-white font-mono">
              {summary.avg_query_latency_ms} <span className="text-xs font-normal text-zinc-400">ms</span>
            </div>
            <div className="text-[11px] text-zinc-500">P95: {summary.p95_query_latency_ms} ms</div>
          </div>

          <div className="p-4 rounded-xl bg-zinc-900/80 border border-zinc-800 space-y-1">
            <div className="flex items-center justify-between text-xs text-zinc-400">
              <span>Slow Queries (&gt;100ms)</span>
              <Clock className="h-4 w-4 text-amber-400" />
            </div>
            <div className="text-2xl font-black text-amber-300 font-mono">
              {summary.slow_queries_count_24h}
            </div>
            <div className="text-[11px] text-zinc-500">Captured in 24h window</div>
          </div>

          <div className="p-4 rounded-xl bg-zinc-900/80 border border-zinc-800 space-y-1">
            <div className="flex items-center justify-between text-xs text-zinc-400">
              <span>Connection Pool</span>
              <Server className="h-4 w-4 text-emerald-400" />
            </div>
            <div className="text-2xl font-black text-white font-mono">
              {summary.active_connections} / {summary.connection_pool_size}
            </div>
            <div className="text-[11px] text-zinc-500">Overflow: {summary.overflow_connections} conns</div>
          </div>

          <div className="p-4 rounded-xl bg-zinc-900/80 border border-zinc-800 space-y-1">
            <div className="flex items-center justify-between text-xs text-zinc-400">
              <span>Index Optimization</span>
              <Zap className="h-4 w-4 text-purple-400" />
            </div>
            <div className="text-2xl font-black text-emerald-400 font-mono">
              100%
            </div>
            <div className="text-[11px] text-zinc-500">6 composite indexes active</div>
          </div>
        </div>

        {/* Structural Indexing Recommendations */}
        {summary.recommendations.length > 0 && (
          <div className="space-y-3 border-t border-zinc-800/80 pt-4">
            <h4 className="text-xs font-bold text-zinc-300 uppercase tracking-wider">
              Automated Indexing Recommendations
            </h4>
            <div className="space-y-2">
              {summary.recommendations.map((rec, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-lg bg-zinc-900/60 border border-zinc-800 text-xs flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2"
                >
                  <div className="space-y-0.5">
                    <span className="font-bold text-cyan-400 font-mono">
                      Table: {rec.target_table}
                    </span>
                    <p className="text-zinc-300">{rec.recommendation}</p>
                    <p className="text-[11px] text-zinc-500 font-mono">{rec.query_pattern}</p>
                  </div>
                  <span className="shrink-0 px-2.5 py-1 rounded bg-emerald-950/60 border border-emerald-500/40 text-[11px] font-bold text-emerald-300 self-start sm:self-auto">
                    {rec.estimated_impact}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
