"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  FindingAttackPathsResponse,
  FindingEvidenceResponse,
  FindingRemediationResponse,
  VulnerabilitiesService,
  VulnerabilityIntelligenceResponse,
} from "@/services/vulnerabilities.service";
import { VulnerabilityHeader } from "@/components/vulnerabilities/vulnerability-header";
import { CVSSRiskCard } from "@/components/vulnerabilities/cvss-risk-card";
import { EvidenceViewerDrawer } from "@/components/vulnerabilities/evidence-viewer-drawer";
import { AttackPathGraph } from "@/components/vulnerabilities/attack-path-graph";
import { AIRemediationDrawer } from "@/components/vulnerabilities/ai-remediation-drawer";

export default function VulnerabilityDetailPage() {
  const params = useParams();
  const findingId = params?.id as string;

  const [vulnerability, setVulnerability] =
    useState<VulnerabilityIntelligenceResponse | null>(null);
  const [evidenceData, setEvidenceData] =
    useState<FindingEvidenceResponse | null>(null);
  const [attackPathData, setAttackPathData] =
    useState<FindingAttackPathsResponse | null>(null);
  const [remediationData, setRemediationData] =
    useState<FindingRemediationResponse | null>(null);

  const [activeTab, setActiveTab] = useState<
    "EVIDENCE" | "ATTACK_PATH" | "AI_REMEDIATION"
  >("EVIDENCE");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!findingId) return;

    async function loadData() {
      try {
        setLoading(true);
        const [vuln, ev, ap, rem] = await Promise.all([
          VulnerabilitiesService.getVulnerabilityDetails(findingId),
          VulnerabilitiesService.getVulnerabilityEvidence(findingId),
          VulnerabilitiesService.getVulnerabilityAttackPaths(findingId),
          VulnerabilitiesService.getVulnerabilityRemediation(findingId),
        ]);
        setVulnerability(vuln);
        setEvidenceData(ev);
        setAttackPathData(ap);
        setRemediationData(rem);
      } catch (err: any) {
        console.error("Error loading vulnerability intelligence:", err);
        setError(err.message || "Failed to load vulnerability investigation record.");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [findingId]);

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="flex items-center gap-3 text-sm text-zinc-400">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-red-500 border-t-transparent" />
          <span>Loading Vulnerability Intelligence Workspace...</span>
        </div>
      </div>
    );
  }

  if (error || !vulnerability) {
    return (
      <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-6 text-center text-red-400">
        <p className="text-sm font-semibold">{error || "Vulnerability record not found."}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Vulnerability Header */}
      <VulnerabilityHeader vulnerability={vulnerability} />

      {/* CVSS & EPSS Scoring Card */}
      <CVSSRiskCard vulnerability={vulnerability} />

      {/* Investigation Navigation Tabs */}
      <div className="flex border-b border-zinc-800">
        <button
          onClick={() => setActiveTab("EVIDENCE")}
          className={`flex items-center gap-2 px-6 py-3 text-xs font-semibold uppercase tracking-wider transition-all border-b-2 ${
            activeTab === "EVIDENCE"
              ? "border-red-500 text-red-400 bg-red-500/5"
              : "border-transparent text-zinc-400 hover:text-zinc-200"
          }`}
        >
          <span>📁 Proof Evidence ({evidenceData?.total_count || 0})</span>
        </button>

        <button
          onClick={() => setActiveTab("ATTACK_PATH")}
          className={`flex items-center gap-2 px-6 py-3 text-xs font-semibold uppercase tracking-wider transition-all border-b-2 ${
            activeTab === "ATTACK_PATH"
              ? "border-red-500 text-red-400 bg-red-500/5"
              : "border-transparent text-zinc-400 hover:text-zinc-200"
          }`}
        >
          <span>🔗 Attack Chain Graph</span>
        </button>

        <button
          onClick={() => setActiveTab("AI_REMEDIATION")}
          className={`flex items-center gap-2 px-6 py-3 text-xs font-semibold uppercase tracking-wider transition-all border-b-2 ${
            activeTab === "AI_REMEDIATION"
              ? "border-red-500 text-red-400 bg-red-500/5"
              : "border-transparent text-zinc-400 hover:text-zinc-200"
          }`}
        >
          <span>✨ AI Remediation Drawer</span>
        </button>
      </div>

      {/* Tab Content Display */}
      {activeTab === "EVIDENCE" && evidenceData && (
        <EvidenceViewerDrawer evidenceItems={evidenceData.evidence_items} />
      )}

      {activeTab === "ATTACK_PATH" && attackPathData && (
        <AttackPathGraph attackPathData={attackPathData} />
      )}

      {activeTab === "AI_REMEDIATION" && remediationData && (
        <AIRemediationDrawer
          findingId={findingId}
          remediationData={remediationData}
        />
      )}
    </div>
  );
}
