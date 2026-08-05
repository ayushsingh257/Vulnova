"use client";

import React, { useEffect, useState } from "react";
import { ShieldCheck, RefreshCw } from "lucide-react";
import { DashboardLayout } from "@/components/dashboard/dashboard-layout";
import {
  OWASPValidationService,
  OWASPValidationSuiteResponse,
  OWASPCategoryResultDTO,
} from "@/services/owasp_validation.service";
import { OWASPPassRateCard } from "@/components/validation/OWASPPassRateCard";
import { OWASPCategoryGrid } from "@/components/validation/OWASPCategoryGrid";
import { OWASPValidationRunButton } from "@/components/validation/OWASPValidationRunButton";
import { OWASPTestDetailsModal } from "@/components/validation/OWASPTestDetailsModal";

export default function OWASPValidationPage() {
  const [suiteResult, setSuiteResult] = useState<OWASPValidationSuiteResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<OWASPCategoryResultDTO | null>(null);

  const fetchResults = async () => {
    setLoading(true);
    try {
      const data = await OWASPValidationService.getResults();
      setSuiteResult(data);
    } catch (err) {
      console.error("Failed to fetch OWASP validation results:", err);
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
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-600/20 border border-purple-500/40 text-purple-400 shadow-md">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-black tracking-tight text-white">
                OWASP Top 10 (2021) Security Validation
              </h1>
              <p className="text-xs text-zinc-400 mt-0.5">
                Automated security assertion suite verifying tenant application posture and active security controls
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
            <OWASPValidationRunButton onRunComplete={setSuiteResult} />
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12 text-zinc-500 text-sm">
            Executing OWASP Top 10 security assertion suite...
          </div>
        ) : suiteResult ? (
          <>
            {/* Top Pass Rate Card */}
            <OWASPPassRateCard
              passRate={suiteResult.overall_pass_rate}
              overallStatus={suiteResult.overall_status}
              passedCount={suiteResult.passed_categories}
              failedCount={suiteResult.failed_categories}
              warningCount={suiteResult.warning_categories}
              executedAt={suiteResult.executed_at}
            />

            {/* OWASP Category Assertion Grid */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                  OWASP Category Assertion Results (A01 - A10)
                </h2>
                <span className="text-xs font-mono text-zinc-400">
                  Suite ID: {suiteResult.suite_id.slice(0, 8)}...
                </span>
              </div>

              <OWASPCategoryGrid
                categories={suiteResult.category_results}
                onSelectCategory={setSelectedCategory}
              />
            </div>
          </>
        ) : (
          <div className="text-center py-12 text-zinc-500 text-sm">
            No validation suite results available. Click run above to execute.
          </div>
        )}

        {/* Slide-in Detail Modal */}
        <OWASPTestDetailsModal
          category={selectedCategory}
          onClose={() => setSelectedCategory(null)}
        />
      </div>
    </DashboardLayout>
  );
}
