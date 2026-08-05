"use client";

import React, { useEffect, useState } from "react";
import { Boxes, RefreshCw } from "lucide-react";
import { DashboardLayout } from "@/components/dashboard/dashboard-layout";
import {
  ContainerValidationService,
  ContainerValidationSuiteResponse,
  ContainerCategoryResultDTO,
} from "@/services/container_validation.service";
import { ContainerPassRateCard } from "@/components/validation/ContainerPassRateCard";
import { ContainerCategoryGrid } from "@/components/validation/ContainerCategoryGrid";
import { ContainerValidationRunButton } from "@/components/validation/ContainerValidationRunButton";
import { ContainerDetailsModal } from "@/components/validation/ContainerDetailsModal";

export default function ContainerValidationPage() {
  const [suiteResult, setSuiteResult] = useState<ContainerValidationSuiteResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<ContainerCategoryResultDTO | null>(null);

  const fetchResults = async () => {
    setLoading(true);
    try {
      const data = await ContainerValidationService.getResults();
      setSuiteResult(data);
    } catch (err) {
      console.error("Failed to fetch container validation results:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResults();
  }, []);

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-zinc-800 pb-6">
          <div className="flex items-center space-x-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-600/20 border border-cyan-500/40 text-cyan-400 shadow-md">
              <Boxes className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-black tracking-tight text-white">
                Container Image Security Audit & Runtime Hardening
              </h1>
              <p className="text-xs text-zinc-400 mt-0.5">
                Automated container security verification engine evaluating base image CVEs, unprivileged execution, Seccomp profiles & cgroup limits
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={fetchResults}
              className="p-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white transition-colors"
              title="Refresh Results"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
            <ContainerValidationRunButton onRunComplete={setSuiteResult} />
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12 text-zinc-500 text-sm">
            Evaluating Container Image Security & Runtime Hardening assertion suite...
          </div>
        ) : suiteResult ? (
          <>
            {/* Top Pass Rate Card */}
            <ContainerPassRateCard
              passRate={suiteResult.overall_pass_rate}
              overallStatus={suiteResult.overall_status}
              passedCount={suiteResult.passed_categories}
              failedCount={suiteResult.failed_categories}
              warningCount={suiteResult.warning_categories}
              executedAt={suiteResult.executed_at}
            />

            {/* Container Category Assertion Grid */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                  Container Security Category Results (CONTAINER1 - CONTAINER10)
                </h2>
                <span className="text-xs font-mono text-zinc-400">
                  Suite ID: {suiteResult.suite_id.slice(0, 8)}...
                </span>
              </div>

              <ContainerCategoryGrid
                categories={suiteResult.category_results}
                onSelectCategory={setSelectedCategory}
              />
            </div>
          </>
        ) : (
          <div className="text-center py-12 text-zinc-500 text-sm">
            No container validation results available. Click run above to execute.
          </div>
        )}

        {/* Slide-in Detail Modal */}
        <ContainerDetailsModal
          category={selectedCategory}
          onClose={() => setSelectedCategory(null)}
        />
      </div>
    </DashboardLayout>
  );
}
