"use client";

import React, { useEffect, useState } from "react";
import { Server, RefreshCw } from "lucide-react";
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
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-zinc-800 pb-6">
        <div className="flex items-center space-x-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600/20 border border-blue-500/40 text-blue-400 shadow-md">
            <Server className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tight text-white">
              API Security & BOLA/JWT Validation Suite
            </h1>
            <p className="text-xs text-zinc-400 mt-0.5">
              Automated assertion suite testing OpenAPI schema compliance, BOLA authorization, JWT signature forgery, and rate limiting
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
          Executing API Security assertion suite...
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
          />

          {/* Category Cards Grid */}
          <APIValidationCategoryGrid
            categories={suiteResult.category_results}
            onSelectCategory={setSelectedCategory}
          />
        </>
      ) : null}

      {/* Slide-over / Modal for Category Details */}
      <APITestDetailsModal
        category={selectedCategory}
        onClose={() => setSelectedCategory(null)}
      />
    </div>
  );
}
