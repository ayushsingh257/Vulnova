"use client";

import React, { useEffect, useState } from "react";
import { ShieldCheck, RefreshCw } from "lucide-react";
import {
  InfrastructureValidationService,
  InfrastructureValidationSuiteResponse,
  InfrastructureValidationCategoryResultDTO,
} from "@/services/infrastructure_validation.service";
import { InfrastructurePassRateCard } from "@/components/validation/InfrastructurePassRateCard";
import { InfrastructureCategoryGrid } from "@/components/validation/InfrastructureCategoryGrid";
import { InfrastructureValidationRunButton } from "@/components/validation/InfrastructureValidationRunButton";
import { InfrastructureTestDetailsModal } from "@/components/validation/InfrastructureTestDetailsModal";

export default function InfrastructureValidationPage() {
  const [suiteResult, setSuiteResult] = useState<InfrastructureValidationSuiteResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<InfrastructureValidationCategoryResultDTO | null>(null);

  const fetchResults = async () => {
    setLoading(true);
    try {
      const data = await InfrastructureValidationService.getResults();
      setSuiteResult(data);
    } catch (err) {
      console.error("Failed to fetch infrastructure security validation results:", err);
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
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-600/20 border border-emerald-500/40 text-emerald-400 shadow-md">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tight text-white">
              Infrastructure & Cloud Hardening Validation Suite
            </h1>
            <p className="text-xs text-zinc-400 mt-0.5">
              Automated assertion engine inspecting TLS 1.3 parameters, HSTS security headers, SSH configurations, and container hosts
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
          <InfrastructureValidationRunButton onRunComplete={setSuiteResult} />
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-zinc-500 text-sm">
          Executing Infrastructure Hardening assertion suite...
        </div>
      ) : suiteResult ? (
        <>
          {/* Top Pass Rate Card */}
          <InfrastructurePassRateCard
            passRate={suiteResult.overall_pass_rate}
            overallStatus={suiteResult.overall_status}
            passedCount={suiteResult.passed_categories}
            failedCount={suiteResult.failed_categories}
            warningCount={suiteResult.warning_categories}
          />

          {/* Category Cards Grid */}
          <InfrastructureCategoryGrid
            categories={suiteResult.category_results}
            onSelectCategory={setSelectedCategory}
          />
        </>
      ) : null}

      {/* Slide-in Detail Modal */}
      <InfrastructureTestDetailsModal
        category={selectedCategory}
        onClose={() => setSelectedCategory(null)}
      />
    </div>
  );
}
