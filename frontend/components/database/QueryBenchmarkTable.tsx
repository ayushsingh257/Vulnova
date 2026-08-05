"use client";

import React from "react";
import { Gauge, CheckCircle2, AlertCircle } from "lucide-react";
import { BenchmarkResult } from "@/services/database_performance.service";

interface QueryBenchmarkTableProps {
  benchmarks: BenchmarkResult[];
}

export const QueryBenchmarkTable: React.FC<QueryBenchmarkTableProps> = ({ benchmarks }) => {
  return (
    <div className="space-y-4 rounded-xl bg-zinc-950 border border-zinc-800 p-6">
      <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
        <div className="flex items-center space-x-2">
          <Gauge className="h-5 w-5 text-cyan-400" />
          <h3 className="text-sm font-bold text-white">Database Query Benchmark Profiling Suite</h3>
        </div>
        <span className="text-xs font-mono text-zinc-400">
          Batch Size: {benchmarks[0]?.total_executions || 10} runs / category
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs font-mono">
          <thead className="bg-zinc-900/80 text-zinc-400 border-b border-zinc-800 uppercase tracking-wider">
            <tr>
              <th className="py-3 px-4">Query Category</th>
              <th className="py-3 px-4">Avg Latency</th>
              <th className="py-3 px-4">P95 Latency</th>
              <th className="py-3 px-4">P99 Latency</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4">Optimization Note</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/60 text-zinc-300">
            {benchmarks.map((row, idx) => (
              <tr key={idx} className="hover:bg-zinc-900/40 transition-colors">
                <td className="py-3 px-4 font-bold text-white">{row.query_category}</td>
                <td className="py-3 px-4 text-cyan-300">{row.avg_duration_ms} ms</td>
                <td className="py-3 px-4 text-amber-300">{row.p95_duration_ms} ms</td>
                <td className="py-3 px-4 text-amber-400">{row.p99_duration_ms} ms</td>
                <td className="py-3 px-4">
                  {row.optimization_status === "OPTIMAL" ? (
                    <span className="inline-flex items-center space-x-1 text-emerald-400 font-bold">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      <span>OPTIMAL</span>
                    </span>
                  ) : (
                    <span className="inline-flex items-center space-x-1 text-amber-400 font-bold">
                      <AlertCircle className="h-3.5 w-3.5" />
                      <span>{row.optimization_status}</span>
                    </span>
                  )}
                </td>
                <td className="py-3 px-4 text-zinc-400 text-[11px] truncate max-w-xs">
                  {row.recommendation}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
