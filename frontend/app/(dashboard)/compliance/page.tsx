"use client";

import React, { useEffect, useState } from "react";
import { Loader2, ShieldCheck, FileCheck, Layers, Lock, Award } from "lucide-react";
import {
  ComplianceOverviewResponse,
  ComplianceControlDTO,
  ComplianceService,
} from "@/services/compliance.service";
import { ComplianceScoreCard } from "@/components/compliance/ComplianceScoreCard";
import {
  FrameworkSelector,
  FRAMEWORKS,
} from "@/components/compliance/FrameworkSelector";
import { ComplianceControlTable } from "@/components/compliance/ComplianceControlTable";
import { ComplianceEvidenceDrawer } from "@/components/compliance/ComplianceEvidenceDrawer";
import { ComplianceExportButton } from "@/components/compliance/ComplianceExportButton";

export default function ComplianceDashboardPage() {
  const [activeFramework, setActiveFramework] = useState<string>("owasp_top10");
  const [overview, setOverview] = useState<ComplianceOverviewResponse | null>(null);
  const [selectedControl, setSelectedControl] = useState<ComplianceControlDTO | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchOverview = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await ComplianceService.getComplianceOverview(activeFramework);
        setOverview(data);
      } catch (err: any) {
        console.error("Failed to load compliance overview:", err);
        setError(err.message || "Failed to load compliance posture data");
      } finally {
        setLoading(false);
      }
    };

    fetchOverview();
  }, [activeFramework]);

  return (
    <div className="space-y-8">
        {/* Page Title Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-zinc-800 pb-6">
          <div>
            <div className="flex items-center space-x-2.5">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-red-600/20 border border-red-500/40 text-red-500 shadow-md">
                <ShieldCheck className="h-6 w-6" />
              </div>
              <div>
                <h1 className="text-2xl font-black tracking-tight text-white">
                  Compliance Framework Intelligence
                </h1>
                <p className="text-xs text-zinc-400 mt-0.5">
                  Automated security posture evaluation mapped to OWASP Top 10, ASVS v4.0, PCI DSS 4.0, and ISO 27001
                </p>
              </div>
            </div>
          </div>

          <ComplianceExportButton framework={activeFramework} />
        </div>

        {/* Framework Selector Tabs */}
        <FrameworkSelector
          activeFramework={activeFramework}
          onSelect={(fwId) => setActiveFramework(fwId)}
        />

        {/* Loading State */}
        {loading ? (
          <div className="p-12 text-center text-zinc-400">
            <Loader2 className="w-8 h-8 animate-spin text-red-400 mx-auto mb-3" />
            <p className="text-sm font-semibold text-zinc-300">
              Evaluating compliance controls against active vulnerability findings...
            </p>
          </div>
        ) : error ? (
          <div className="rounded-xl border border-red-900/60 bg-red-950/20 p-6 text-center text-red-400 text-xs font-semibold">
            {error}
          </div>
        ) : overview ? (
          <div className="space-y-8">
            {/* Score Card */}
            <ComplianceScoreCard score={overview.score} />

            {/* Top Remediation Priorities for Failed Controls */}
            {overview.top_remediation_priorities.length > 0 && (
              <div className="rounded-xl border border-amber-900/40 bg-amber-950/20 p-6 space-y-4">
                <h3 className="text-sm font-bold text-amber-400 uppercase tracking-wider flex items-center space-x-2">
                  <Award className="h-4 w-4" />
                  <span>High-Priority Compliance Remediation Actions</span>
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {overview.top_remediation_priorities.map((item) => (
                    <div
                      key={item.control_id}
                      className="rounded-lg border border-zinc-800 bg-zinc-900/80 p-4 space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-bold text-red-400">
                          {item.control_id}
                        </span>
                        <span className="text-[11px] font-mono text-amber-400">
                          {item.affected_findings_count} Open Findings
                        </span>
                      </div>
                      <div className="text-xs font-semibold text-zinc-200">
                        {item.title}
                      </div>
                      <p className="text-[11px] text-zinc-400">
                        {item.remediation_guidance}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Controls Evaluation Table */}
            <ComplianceControlTable
              controls={overview.controls}
              onSelectControl={(ctrl) => setSelectedControl(ctrl)}
            />
          </div>
        ) : null}

        {/* Evidence Traceability Drawer */}
        <ComplianceEvidenceDrawer
          control={selectedControl}
          onClose={() => setSelectedControl(null)}
        />
      </div>
  );
}
