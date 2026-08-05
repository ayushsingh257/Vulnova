"use client";

import React, { useEffect, useState } from "react";
import { Database, Play, RefreshCw, Loader2, AlertCircle } from "lucide-react";
import { DashboardLayout } from "@/components/dashboard/dashboard-layout";
import {
  DatabasePerformanceService,
  DatabaseHealthSummary,
  BenchmarkResult,
  SlowQueryLog,
} from "@/services/database_performance.service";
import { DatabasePerformanceCard } from "@/components/database/DatabasePerformanceCard";
import { QueryBenchmarkTable } from "@/components/database/QueryBenchmarkTable";

export default function DatabasePerformancePage() {
  const [healthSummary, setHealthSummary] = useState<DatabaseHealthSummary | null>(null);
  const [benchmarks, setBenchmarks] = useState<BenchmarkResult[]>([]);
  const [slowQueries, setSlowQueries] = useState<SlowQueryLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [benchmarking, setBenchmarking] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [health, bench, slow] = await Promise.all([
        DatabasePerformanceService.getHealth(),
        DatabasePerformanceService.runBenchmark(10),
        DatabasePerformanceService.getSlowQueries(),
      ]);
      setHealthSummary(health);
      setBenchmarks(bench);
      setSlowQueries(slow);
    } catch (err) {
      console.error("Failed to fetch database performance data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleTriggerBenchmark = async () => {
    setBenchmarking(true);
    try {
      const results = await DatabasePerformanceService.runBenchmark(20);
      setBenchmarks(results);
      const health = await DatabasePerformanceService.getHealth();
      setHealthSummary(health);
    } catch (err) {
      console.error("Failed to execute benchmark suite:", err);
    } finally {
      setBenchmarking(false);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-8 max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-zinc-800 pb-6">
          <div className="flex items-center space-x-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-600/20 border border-cyan-500/40 text-cyan-400 shadow-md">
              <Database className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-black tracking-tight text-white">
                Database Query Optimization & Index Performance
              </h1>
              <p className="text-xs text-zinc-400 mt-0.5">
                PostgreSQL query execution profiling, composite indexing analysis, and connection pool health
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={handleTriggerBenchmark}
              disabled={benchmarking || loading}
              className="px-4 py-2 rounded-lg bg-cyan-600 font-bold text-xs text-white hover:bg-cyan-500 transition-colors disabled:opacity-50 flex items-center space-x-2 shadow-md"
            >
              {benchmarking ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Profiling Queries...</span>
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 fill-current" />
                  <span>Run Benchmark Suite</span>
                </>
              )}
            </button>
            <button
              onClick={fetchData}
              className="p-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white transition-colors"
              title="Refresh Data"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-16 text-zinc-500 text-sm">
            Analyzing database performance metrics and query latency...
          </div>
        ) : (
          <>
            {healthSummary && <DatabasePerformanceCard summary={healthSummary} />}

            {benchmarks.length > 0 && <QueryBenchmarkTable benchmarks={benchmarks} />}

            {/* Slow Queries Section */}
            <div className="space-y-4 rounded-xl bg-zinc-950 border border-zinc-800 p-6">
              <h3 className="text-sm font-bold text-white flex items-center space-x-2">
                <AlertCircle className="h-4 w-4 text-amber-400" />
                <span>Captured Slow Query Execution Logs (&gt;100ms)</span>
              </h3>
              {slowQueries.length === 0 ? (
                <div className="p-4 rounded-lg bg-zinc-900/60 border border-zinc-800 text-xs text-emerald-400 font-mono text-center">
                  ✅ Zero slow queries (&gt;100ms) detected in recent execution logs.
                </div>
              ) : (
                <div className="space-y-2 font-mono text-xs">
                  {slowQueries.map((log, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-lg bg-zinc-900 border border-zinc-800 flex items-start justify-between gap-4"
                    >
                      <div className="space-y-1 truncate">
                        <span className="text-zinc-400 text-[11px] block">
                          Table: {log.table_name || "Unknown"} | {new Date(log.timestamp).toLocaleString()}
                        </span>
                        <code className="text-amber-300 block truncate">{log.statement}</code>
                      </div>
                      <span className="shrink-0 font-bold text-amber-400 bg-amber-950/40 border border-amber-800/60 px-2 py-1 rounded">
                        {log.duration_ms} ms
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </DashboardLayout>
  );
}
