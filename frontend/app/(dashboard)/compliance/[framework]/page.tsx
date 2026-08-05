"use client";

import React, { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2, ArrowLeft, ShieldCheck } from "lucide-react";
import { DashboardLayout } from "@/components/dashboard/dashboard-layout";
import {
  ComplianceOverviewResponse,
  ComplianceControlDTO,
  ComplianceService,
} from "@/services/compliance.service";
import { ComplianceScoreCard } from "@/components/compliance/ComplianceScoreCard";
import {
  FrameworkSelector,
} from "@/components/compliance/FrameworkSelector";
import { ComplianceControlTable } from "@/components/compliance/ComplianceControlTable";
import { ComplianceEvidenceDrawer } from "@/components/compliance/ComplianceEvidenceDrawer";
import { ComplianceExportButton } from "@/components/compliance/ComplianceExportButton";

export default function ComplianceFrameworkDetailPage() {
  const params = useParams();
  const router = useRouter();
  const frameworkId = (params?.framework as string) || "owasp_top10";

  const [overview, setOverview] = useState<ComplianceOverviewResponse | null>(null);
  const [selectedControl, setSelectedControl] = useState<ComplianceControlDTO | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchOverview = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await ComplianceService.getComplianceOverview(frameworkId);
        setOverview(data);
      } catch (err: any) {
        console.error("Failed to load compliance framework detail:", err);
        setError(err.message || "Failed to load framework compliance data");
      } finally {
        setLoading(false);
      }
    };

    fetchOverview();
  }, [frameworkId]);

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Navigation back button */}
        <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
          <button
            onClick={() => router.push("/compliance")}
            className="flex items-center space-x-2 text-xs font-semibold text-zinc-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Back to Compliance Dashboard</span>
          </button>
          <ComplianceExportButton framework={frameworkId} />
        </div>

        {/* Framework Selector Tabs */}
        <FrameworkSelector
          activeFramework={frameworkId}
          onSelect={(fwId) => router.push(`/compliance/${fwId}`)}
        />

        {/* Loading State */}
        {loading ? (
          <div className="p-12 text-center text-zinc-400">
            <Loader2 className="w-8 h-8 animate-spin text-red-400 mx-auto mb-3" />
            <p className="text-sm font-semibold text-zinc-300">
              Evaluating compliance controls for framework...
            </p>
          </div>
        ) : error ? (
          <div className="rounded-xl border border-red-900/60 bg-red-950/20 p-6 text-center text-red-400 text-xs font-semibold">
            {error}
          </div>
        ) : overview ? (
          <div className="space-y-8">
            <ComplianceScoreCard score={overview.score} />
            <ComplianceControlTable
              controls={overview.controls}
              onSelectControl={(ctrl) => setSelectedControl(ctrl)}
            />
          </div>
        ) : null}

        <ComplianceEvidenceDrawer
          control={selectedControl}
          onClose={() => setSelectedControl(null)}
        />
      </div>
    </DashboardLayout>
  );
}
