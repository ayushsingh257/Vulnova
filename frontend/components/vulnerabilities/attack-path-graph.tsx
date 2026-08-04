"use client";

import React from "react";
import { FindingAttackPathsResponse } from "@/services/vulnerabilities.service";

interface AttackPathGraphProps {
  attackPathData: FindingAttackPathsResponse;
}

export const AttackPathGraph: React.FC<AttackPathGraphProps> = ({
  attackPathData,
}) => {
  const getImpactBadge = (impact: string) => {
    switch (impact.toUpperCase()) {
      case "CRITICAL":
        return "bg-red-500/10 text-red-400 border-red-500/20";
      case "HIGH":
        return "bg-orange-500/10 text-orange-400 border-orange-500/20";
      case "MEDIUM":
        return "bg-yellow-500/10 text-yellow-400 border-yellow-500/20";
      default:
        return "bg-blue-500/10 text-blue-400 border-blue-500/20";
    }
  };

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-6">
      <div className="border-b border-zinc-800 pb-4">
        <h3 className="text-lg font-bold text-zinc-100">
          {attackPathData.title}
        </h3>
        <p className="text-xs text-zinc-400 mt-1">
          {attackPathData.attack_summary}
        </p>
      </div>

      <div className="mt-8 flex flex-col items-center gap-4 max-w-2xl mx-auto">
        {attackPathData.nodes.map((node, idx) => (
          <React.Fragment key={node.id}>
            {/* Connector Line */}
            {idx > 0 && (
              <div className="flex flex-col items-center my-1">
                <div className="h-6 w-0.5 bg-gradient-to-b from-red-500/60 to-zinc-700" />
                <span className="text-[10px] uppercase font-mono font-semibold tracking-wider text-zinc-500 bg-zinc-900 px-2 py-0.5 rounded border border-zinc-800">
                  {node.relationship}
                </span>
                <div className="h-6 w-0.5 bg-gradient-to-b from-zinc-700 to-red-500/60" />
              </div>
            )}

            {/* Node Card */}
            <div className="w-full rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 shadow-sm transition-all hover:border-zinc-700">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full border border-zinc-700 bg-zinc-800 text-xs font-black text-zinc-200">
                    {node.sequence_number}
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-zinc-100">
                      {node.asset_name}
                    </h4>
                    <p className="text-xs font-medium text-zinc-400">
                      {node.asset_type}
                    </p>
                  </div>
                </div>

                <span
                  className={`rounded border px-2 py-0.5 text-[10px] font-semibold uppercase ${getImpactBadge(
                    node.risk_impact
                  )}`}
                >
                  {node.risk_impact} Impact
                </span>
              </div>

              <div className="mt-3 rounded bg-zinc-950/80 p-2.5 border border-zinc-800/60">
                <p className="text-xs text-zinc-300 font-medium">
                  {node.vulnerability_title}
                </p>
              </div>
            </div>
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};
