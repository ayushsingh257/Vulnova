"use client";

import React, { useEffect, useState } from "react";
import { ShieldCheck, RefreshCw } from "lucide-react";
import {
  ThreatValidationService,
  ThreatValidationSuiteResponse,
  ThreatCategoryResultDTO,
} from "@/services/threat_validation.service";
import { ThreatPassRateCard } from "@/components/validation/ThreatPassRateCard";
import { ThreatCategoryGrid } from "@/components/validation/ThreatCategoryGrid";
import { ThreatValidationRunButton } from "@/components/validation/ThreatValidationRunButton";
import { ThreatDetailsModal } from "@/components/validation/ThreatDetailsModal";

export default function ThreatValidationPage() {
  const [suiteResult, setSuiteResult] = useState<ThreatValidationSuiteResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<ThreatCategoryResultDTO | null>(null);

  const fetchResults = async () => {
    setLoading(true);
    try {
      const data = await ThreatValidationService.getResults();
      setSuiteResult(data);
    } catch (err) {
      console.error("Failed to fetch threat model validation results:", err);
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
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-orange-600/20 border border-orange-500/40 text-orange-400 shadow-md">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tight text-white">
              STRIDE Automated Threat Model Validation
            </h1>
            <p className="text-xs text-zinc-400 mt-0.5">
              Automated threat modeling assertion engine evaluating Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, and Elevation of Privilege
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
          <ThreatValidationRunButton onRunComplete={setSuiteResult} />
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-zinc-500 text-sm">
          Executing STRIDE Threat Model assertion suite...
        </div>
      ) : suiteResult ? (
        <>
          {/* Top Pass Rate Card */}
          <ThreatPassRateCard
            passRate={suiteResult.overall_pass_rate}
            overallStatus={suiteResult.overall_status}
            passedCount={suiteResult.passed_categories}
            failedCount={suiteResult.failed_categories}
            warningCount={suiteResult.warning_categories}
          />

          {/* Threat Category Assertion Grid */}
          <ThreatCategoryGrid
            categories={suiteResult.category_results}
            onSelectCategory={setSelectedCategory}
          />
        </>
      ) : null}

      {/* Slide-in Detail Modal */}
      <ThreatDetailsModal
        category={selectedCategory}
        onClose={() => setSelectedCategory(null)}
      />
    </div>
  );
}
