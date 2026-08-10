"use client";

import React, { useEffect, useState } from "react";
import { ShieldAlert, RefreshCw } from "lucide-react";
import {
  RegressionValidationService,
  RegressionValidationSuiteResponse,
  RegressionCategoryResultDTO,
} from "@/services/regression_validation.service";
import { RegressionPassRateCard } from "@/components/validation/RegressionPassRateCard";
import { RegressionCategoryGrid } from "@/components/validation/RegressionCategoryGrid";
import { RegressionValidationRunButton } from "@/components/validation/RegressionValidationRunButton";
import { RegressionDetailsModal } from "@/components/validation/RegressionDetailsModal";

export default function RegressionValidationPage() {
  const [suiteResult, setSuiteResult] = useState<RegressionValidationSuiteResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<RegressionCategoryResultDTO | null>(null);

  const fetchResults = async () => {
    setLoading(true);
    try {
      const data = await RegressionValidationService.getResults();
      setSuiteResult(data);
    } catch (err) {
      console.error("Failed to fetch automated regression validation results:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResults();
  }, []);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-zinc-800 pb-6">
        <div className="flex items-center space-x-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-600/20 border border-teal-500/40 text-teal-400 shadow-md">
            <ShieldAlert className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tight text-white">
              Automated Vulnerability Patch Regression Suite
            </h1>
            <p className="text-xs text-zinc-400 mt-0.5">
              Automated regression assertion engine verifying resolved vulnerability fixes, prevent re-introduction, and validate patch stability
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
          <RegressionValidationRunButton onRunComplete={setSuiteResult} />
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-zinc-500 text-sm">
          Executing Patch Regression assertion suite...
        </div>
      ) : suiteResult ? (
        <>
          {/* Top Pass Rate Card */}
          <RegressionPassRateCard
            passRate={suiteResult.overall_pass_rate}
            overallStatus={suiteResult.overall_status}
            passedCount={suiteResult.passed_categories}
            failedCount={suiteResult.failed_categories}
            warningCount={suiteResult.warning_categories}
          />

          {/* Regression Category Assertion Grid */}
          <RegressionCategoryGrid
            categories={suiteResult.category_results}
            onSelectCategory={setSelectedCategory}
          />
        </>
      ) : null}

      {/* Slide-in Detail Modal */}
      <RegressionDetailsModal
        category={selectedCategory}
        onClose={() => setSelectedCategory(null)}
      />
    </div>
  );
}
