"use client";

import React, { useEffect, useState } from "react";
import { PackageCheck, RefreshCw } from "lucide-react";
import { DashboardLayout } from "@/components/dashboard/dashboard-layout";
import {
  SCAValidationService,
  SCAValidationSuiteResponse,
  SCACategoryResultDTO,
} from "@/services/sca_validation.service";
import { SCAPassRateCard } from "@/components/validation/SCAPassRateCard";
import { SCACategoryGrid } from "@/components/validation/SCACategoryGrid";
import { SCAValidationRunButton } from "@/components/validation/SCAValidationRunButton";
import { SCADetailsModal } from "@/components/validation/SCADetailsModal";

export default function SCAValidationPage() {
  const [suiteResult, setSuiteResult] = useState<SCAValidationSuiteResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<SCACategoryResultDTO | null>(null);

  const fetchResults = async () => {
    setLoading(true);
    try {
      const data = await SCAValidationService.getResults();
      setSuiteResult(data);
    } catch (err) {
      console.error("Failed to fetch dependency validation results:", err);
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
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600/20 border border-blue-500/40 text-blue-400 shadow-md">
              <PackageCheck className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-black tracking-tight text-white">
                Dependency Security Audit & SCA Enforcement
              </h1>
              <p className="text-xs text-zinc-400 mt-0.5">
                Automated Software Composition Analysis engine verifying third-party packages, CVEs, lockfile integrity & license compliance
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
            <SCAValidationRunButton onRunComplete={setSuiteResult} />
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12 text-zinc-500 text-sm">
            Evaluating Dependency Security & Software Composition assertion suite...
          </div>
        ) : suiteResult ? (
          <>
            {/* Top Pass Rate Card */}
            <SCAPassRateCard
              passRate={suiteResult.overall_pass_rate}
              overallStatus={suiteResult.overall_status}
              passedCount={suiteResult.passed_categories}
              failedCount={suiteResult.failed_categories}
              warningCount={suiteResult.warning_categories}
              executedAt={suiteResult.executed_at}
            />

            {/* SCA Category Assertion Grid */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                  SCA Category Control Results (SCA1 - SCA10)
                </h2>
                <span className="text-xs font-mono text-zinc-400">
                  Suite ID: {suiteResult.suite_id.slice(0, 8)}...
                </span>
              </div>

              <SCACategoryGrid
                categories={suiteResult.category_results}
                onSelectCategory={setSelectedCategory}
              />
            </div>
          </>
        ) : (
          <div className="text-center py-12 text-zinc-500 text-sm">
            No dependency validation results available. Click run above to execute.
          </div>
        )}

        {/* Slide-in Detail Modal */}
        <SCADetailsModal
          category={selectedCategory}
          onClose={() => setSelectedCategory(null)}
        />
      </div>
    </DashboardLayout>
  );
}
