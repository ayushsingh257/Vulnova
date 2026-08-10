"use client";

import React, { useEffect, useState } from "react";
import { KeyRound, RefreshCw } from "lucide-react";
import {
  SecretsValidationService,
  SecretsValidationSuiteResponse,
  SecretCategoryResultDTO,
} from "@/services/secrets_validation.service";
import { SecretsPassRateCard } from "@/components/validation/SecretsPassRateCard";
import { SecretsCategoryGrid } from "@/components/validation/SecretsCategoryGrid";
import { SecretsValidationRunButton } from "@/components/validation/SecretsValidationRunButton";
import { SecretsDetailsModal } from "@/components/validation/SecretsDetailsModal";

export default function SecretsValidationPage() {
  const [suiteResult, setSuiteResult] = useState<SecretsValidationSuiteResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<SecretCategoryResultDTO | null>(null);

  const fetchResults = async () => {
    setLoading(true);
    try {
      const data = await SecretsValidationService.getResults();
      setSuiteResult(data);
    } catch (err) {
      console.error("Failed to fetch secrets validation results:", err);
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
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-600/20 border border-purple-500/40 text-purple-400 shadow-md">
            <KeyRound className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tight text-white">
              Secrets Audit & Hardcoded Credential Detection
            </h1>
            <p className="text-xs text-zinc-400 mt-0.5">
              Automated secret scanning engine detecting exposed API keys, private keys, cloud tokens, and password entropy in code
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
          <SecretsValidationRunButton onRunComplete={setSuiteResult} />
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-zinc-500 text-sm">
          Executing Secrets Audit assertion suite...
        </div>
      ) : suiteResult ? (
        <>
          {/* Top Pass Rate Card */}
          <SecretsPassRateCard
            passRate={suiteResult.overall_pass_rate}
            overallStatus={suiteResult.overall_status}
            passedCount={suiteResult.passed_categories}
            failedCount={suiteResult.failed_categories}
            warningCount={suiteResult.warning_categories}
          />

          {/* Secrets Category Assertion Grid */}
          <SecretsCategoryGrid
            categories={suiteResult.category_results}
            onSelectCategory={setSelectedCategory}
          />
        </>
      ) : null}

      {/* Slide-in Detail Modal */}
      <SecretsDetailsModal
        category={selectedCategory}
        onClose={() => setSelectedCategory(null)}
      />
    </div>
  );
}
