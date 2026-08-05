"use client";

import React, { useEffect, useState } from "react";
import { Award, RefreshCw } from "lucide-react";
import { DashboardLayout } from "@/components/dashboard/dashboard-layout";
import {
  CertificationValidationService,
  CertificationValidationSuiteResponse,
  CertificationCategoryResultDTO,
} from "@/services/certification_validation.service";
import { CertificationScoreCard } from "@/components/validation/CertificationScoreCard";
import { CertificationCategoryGrid } from "@/components/validation/CertificationCategoryGrid";
import { CertificationValidationRunButton } from "@/components/validation/CertificationValidationRunButton";
import { CertificationDetailsModal } from "@/components/validation/CertificationDetailsModal";

export default function CertificationValidationPage() {
  const [suiteResult, setSuiteResult] = useState<CertificationValidationSuiteResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<CertificationCategoryResultDTO | null>(null);

  const fetchResults = async () => {
    setLoading(true);
    try {
      const data = await CertificationValidationService.getResults();
      setSuiteResult(data);
    } catch (err) {
      console.error("Failed to fetch certification validation results:", err);
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
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-600/20 border border-amber-500/40 text-amber-400 shadow-md">
              <Award className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-black tracking-tight text-white">
                Security Control Plane Final Certification & Compliance
              </h1>
              <p className="text-xs text-zinc-400 mt-0.5">
                Enterprise security certification framework validating complete control coverage across OWASP, Infra, Pentest, SCA, Containers, Secrets, STRIDE, Regression, Governance & Production Readiness
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
            <CertificationValidationRunButton onRunComplete={setSuiteResult} />
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12 text-zinc-500 text-sm">
            Evaluating Security Control Plane Final Certification assertion suite...
          </div>
        ) : suiteResult ? (
          <>
            {/* Top Score Card */}
            <CertificationScoreCard
              certificationScore={suiteResult.overall_certification_score}
              overallStatus={suiteResult.overall_status}
              passedCount={suiteResult.passed_categories}
              failedCount={suiteResult.failed_categories}
              warningCount={suiteResult.warning_categories}
              executedAt={suiteResult.executed_at}
            />

            {/* Certification Category Assertion Grid */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                  Security Control Domain Certification Results (CERTIFICATION1 - CERTIFICATION10)
                </h2>
                <span className="text-xs font-mono text-zinc-400">
                  Suite ID: {suiteResult.suite_id.slice(0, 8)}...
                </span>
              </div>

              <CertificationCategoryGrid
                categories={suiteResult.category_results}
                onSelectCategory={setSelectedCategory}
              />
            </div>
          </>
        ) : (
          <div className="text-center py-12 text-zinc-500 text-sm">
            No certification validation results available. Click run above to execute.
          </div>
        )}

        {/* Slide-in Detail Modal */}
        <CertificationDetailsModal
          category={selectedCategory}
          onClose={() => setSelectedCategory(null)}
        />
      </div>
    </DashboardLayout>
  );
}
