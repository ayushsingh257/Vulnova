"use client";

import React, { useEffect, useState } from "react";
import { PackageCheck, RefreshCw } from "lucide-react";
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
      console.error("Failed to fetch SCA validation results:", err);
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
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600/20 border border-blue-500/40 text-blue-400 shadow-md">
            <PackageCheck className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tight text-white">
              Software Composition Analysis (SCA) & Dependency Security
            </h1>
            <p className="text-xs text-zinc-400 mt-0.5">
              Automated dependency audit engine inspecting package manifests, open-source CVE vulnerabilities, and license compliance
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
          Executing Software Composition Analysis assertion suite...
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
          />

          {/* SCA Category Assertion Grid */}
          <SCACategoryGrid
            categories={suiteResult.category_results}
            onSelectCategory={setSelectedCategory}
          />
        </>
      ) : null}

      {/* Slide-over / Modal for Category Details */}
      <SCADetailsModal
        category={selectedCategory}
        onClose={() => setSelectedCategory(null)}
      />
    </div>
  );
}
