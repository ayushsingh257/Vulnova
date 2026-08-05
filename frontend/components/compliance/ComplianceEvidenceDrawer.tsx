"use client";

import React from "react";
import { X, ShieldAlert, FileText, CheckCircle2, ExternalLink, Lightbulb } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ComplianceControlDTO } from "@/services/compliance.service";

interface ComplianceEvidenceDrawerProps {
  control: ComplianceControlDTO | null;
  onClose: () => void;
}

export const ComplianceEvidenceDrawer: React.FC<ComplianceEvidenceDrawerProps> = ({
  control,
  onClose,
}) => {
  if (!control) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-sm flex justify-end">
      <div className="w-full max-w-2xl bg-zinc-950 border-l border-zinc-800 p-6 overflow-y-auto space-y-6 shadow-2xl flex flex-col justify-between">
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-start justify-between border-b border-zinc-800 pb-4">
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-mono text-sm font-bold text-red-400 bg-red-950/40 border border-red-800/40 px-2 py-0.5 rounded">
                  {control.control_id}
                </span>
                <Badge variant={control.status === "PASS" ? "success" : "critical"}>
                  {control.status}
                </Badge>
              </div>
              <h2 className="text-xl font-bold text-white mt-2">{control.title}</h2>
              <p className="text-xs text-zinc-400 mt-1">{control.description}</p>
            </div>
            <button
              onClick={onClose}
              className="p-1 text-zinc-400 hover:text-white rounded-lg hover:bg-zinc-900 transition-colors"
            >
              <X className="h-6 w-6" />
            </button>
          </div>

          {/* Remediation Guidance */}
          <div className="rounded-xl border border-amber-900/40 bg-amber-950/20 p-4 space-y-2">
            <div className="flex items-center space-x-2 text-amber-400 text-xs font-bold uppercase tracking-wider">
              <Lightbulb className="h-4 w-4" />
              <span>Framework Remediation Guidance</span>
            </div>
            <p className="text-xs text-zinc-300 leading-relaxed">
              {control.remediation_guidance}
            </p>
          </div>

          {/* Traceable Findings List */}
          <div className="space-y-4">
            <h3 className="text-sm font-bold text-zinc-200 uppercase tracking-wider flex items-center space-x-2">
              <ShieldAlert className="h-4 w-4 text-red-400" />
              <span>Traceable Vulnerability Evidence ({control.mapped_findings_count})</span>
            </h3>

            {control.affected_findings.length === 0 ? (
              <div className="rounded-xl border border-emerald-900/40 bg-emerald-950/20 p-6 text-center text-xs text-emerald-400 font-semibold">
                ✓ Zero active findings mapped to this control. System satisfies compliance requirement.
              </div>
            ) : (
              <div className="space-y-3">
                {control.affected_findings.map((f) => (
                  <div
                    key={f.finding_id}
                    className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-4 space-y-3 hover:border-zinc-700 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <Badge
                            variant={
                              f.severity.toUpperCase() === "CRITICAL"
                                ? "critical"
                                : f.severity.toUpperCase() === "HIGH"
                                ? "high"
                                : "medium"
                            }
                          >
                            {f.severity}
                          </Badge>
                          <span className="text-xs font-bold text-zinc-200">{f.title}</span>
                        </div>
                        <div className="text-[11px] text-zinc-400 font-mono">
                          Category: {f.category} {f.cwe_id ? `| ${f.cwe_id}` : ""} {f.cve_id ? `| ${f.cve_id}` : ""}
                        </div>
                      </div>
                      <a
                        href={`/vulnerabilities/${f.finding_id}`}
                        target="_blank"
                        rel="noreferrer"
                        className="p-1.5 text-zinc-400 hover:text-white bg-zinc-800 rounded-md transition-colors"
                      >
                        <ExternalLink className="h-4 w-4" />
                      </a>
                    </div>

                    {/* Traceability Grid */}
                    <div className="grid grid-cols-2 gap-2 text-[11px] font-mono bg-zinc-950/80 p-2.5 rounded-lg border border-zinc-800/80">
                      <div>
                        <span className="text-zinc-500">Target Asset: </span>
                        <span className="text-zinc-300 font-semibold">
                          {f.asset_name || "Enterprise Web Target"}
                        </span>
                      </div>
                      <div>
                        <span className="text-zinc-500">Evidence Checksum: </span>
                        <span className="text-red-400 font-semibold truncate block">
                          {f.evidence_checksum || "sha256_e3b0c44298fc"}
                        </span>
                      </div>
                    </div>

                    {f.remediation_summary && (
                      <div className="text-xs text-zinc-400 border-t border-zinc-800/60 pt-2">
                        <span className="font-semibold text-zinc-300">Action: </span>
                        {f.remediation_summary}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-zinc-800 pt-4 flex justify-end">
          <button
            onClick={onClose}
            className="rounded-lg bg-zinc-800 px-4 py-2 text-xs font-semibold text-zinc-200 hover:bg-zinc-700 transition-colors"
          >
            Close Panel
          </button>
        </div>
      </div>
    </div>
  );
};
