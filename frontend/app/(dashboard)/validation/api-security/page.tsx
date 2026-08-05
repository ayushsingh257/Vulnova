"use client";

import React, { useEffect, useState } from "react";
import { Server, RefreshCw } from "lucide-react";
import { DashboardLayout } from "@/components/dashboard/dashboard-layout";
import {
  APISecurityValidationService,
  APIValidationSuiteResponse,
  APIValidationCategoryResultDTO,
} from "@/services/api_security_validation.service";
import { APIValidationPassRateCard } from "@/components/validation/APIValidationPassRateCard";
import { APIValidationCategoryGrid } from "@/components/validation/APIValidationCategoryGrid";
import { APIValidationRunButton } from "@/components/validation/APIValidationRunButton";
import { APITestDetailsModal } from "@/components/validation/APITestDetailsModal";

export default function APISecurityValidationPage() {
  const [suiteResult, setSuiteResult] = useState<APIValidationSuiteResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<APIValidationCategoryResultDTO | null>(null);

  const fetchResults = async () => {
    setLoading(true);
    try {
      const data = await APISecurityValidationService.getResults();
      setSuiteResult(data);
    } catch (err) {
      console.error("Failed to fetch API security validation results:", err);
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
              <Server className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-black tracking-tight text-white">
                OWASP API Security Top 10 (2023) Validation
              </h1>
              <p className="text-xs text-zinc-400 mt-0.5">
                Automated API endpoint security assertion engine verifying tenant REST routes and security controls
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
            <APIValidationRunButton onRunComplete={setSuiteResult} />
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12 text-zinc-500 text-sm">
            Executing OWASP API Security Top 10 assertion suite...
          </div>
        ) : suiteResult ? (
          <>
            {/* Top Pass Rate Card */}
            <APIValidationPassRateCard
              passRate={suiteResult.overall_pass_rate}
              overallStatus={suiteResult.overall_status}
              passedCount={suiteResult.passed_categories}
              failedCount={suiteResult.failed_categories}
              warningCount={suiteResult.warning_categories}
              executedAt={suiteResult.executed_at}
            />

            {/* OWASP API Category Assertion Grid */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                  OWASP API Category Assertion Results (API1 - API10)
                </h2>
                <span className="text-xs font-mono text-zinc-400">
                  Suite ID: {suiteResult.suite_id.slice(0, 8)}...
                </span>
              </div>

              <APIValidationCategoryGrid
                categories={suiteResult.category_results}
                onSelectCategory={setSelectedCategory}
              />
            </div>
          </>
        ) : (
          <div className="text-center py-12 text-zinc-500 text-sm">
            No API security validation results available. Click run above to execute.
          </div>
        )}

        {/* Slide-in Detail Modal */}
        <APITestDetailsModal
          category={selectedCategory}
          onClose={() => setSelectedCategory(null)}
        />
      </div>
    </DashboardLayout>
  );
}
