"use client";

import React from "react";
import { VulnerabilityIntelligenceResponse } from "@/services/vulnerabilities.service";

interface CVSSRiskCardProps {
  vulnerability: VulnerabilityIntelligenceResponse;
}

export const CVSSRiskCard: React.FC<CVSSRiskCardProps> = ({ vulnerability }) => {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
      {/* CVSS Scoring Card */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-5">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">
          CVSS Risk Breakdown
        </h3>
        <div className="mt-4 flex items-center justify-between">
          <div>
            <p className="text-3xl font-extrabold text-red-400">
              {vulnerability.cvss.base_score.toFixed(1)} / 10.0
            </p>
            <p className="text-xs text-zinc-400">
              Vector: {vulnerability.cvss.vector_string || "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"}
            </p>
          </div>
          <div className="rounded-lg bg-zinc-900 px-3 py-2 text-right">
            <p className="text-xs text-zinc-400">Composite Risk</p>
            <p className="text-xl font-bold text-amber-400">
              {vulnerability.risk_context.composite_risk_score.toFixed(1)}
            </p>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3 pt-3 border-t border-zinc-800/60">
          <div>
            <p className="text-xs text-zinc-400">Exploitability Score</p>
            <p className="text-sm font-semibold text-zinc-200">
              {vulnerability.cvss.exploitability_score
                ? vulnerability.cvss.exploitability_score.toFixed(1)
                : "3.9"}
            </p>
          </div>
          <div>
            <p className="text-xs text-zinc-400">Impact Score</p>
            <p className="text-sm font-semibold text-zinc-200">
              {vulnerability.cvss.impact_score
                ? vulnerability.cvss.impact_score.toFixed(1)
                : "5.9"}
            </p>
          </div>
        </div>
      </div>

      {/* EPSS & Triage Status Card */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-5">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-zinc-400">
          Exploit Prediction & Triage State
        </h3>
        <div className="mt-4 flex items-center justify-between">
          <div>
            <p className="text-xs text-zinc-400">EPSS Exploit Likelihood</p>
            <p className="text-2xl font-extrabold text-amber-400">
              {(vulnerability.epss.epss_score * 100).toFixed(1)}%
            </p>
            <p className="text-xs text-zinc-400">
              Percentile Rank: {(vulnerability.epss.percentile * 100).toFixed(0)}th
            </p>
          </div>
          <div className="rounded-lg bg-zinc-900 px-3 py-2 text-right">
            <p className="text-xs text-zinc-400">Triage Status</p>
            <p className="text-sm font-bold text-emerald-400">
              {vulnerability.triage_status}
            </p>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-zinc-800/60">
          <p className="text-xs text-zinc-400">Remediation Description</p>
          <p className="mt-1 text-xs text-zinc-300 line-clamp-2">
            {vulnerability.remediation ||
              "Apply recommended patches and validate input parameters to mitigate vulnerability."}
          </p>
        </div>
      </div>
    </div>
  );
};
