"use client";

import React from "react";
import { CheckCircle2, XCircle, ChevronRight, ShieldAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ComplianceControlDTO } from "@/services/compliance.service";

interface ComplianceControlTableProps {
  controls: ComplianceControlDTO[];
  onSelectControl: (control: ComplianceControlDTO) => void;
}

export const ComplianceControlTable: React.FC<ComplianceControlTableProps> = ({
  controls,
  onSelectControl,
}) => {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950/80 backdrop-blur-md overflow-hidden shadow-xl">
      <div className="px-6 py-4 border-b border-zinc-800 flex items-center justify-between">
        <h3 className="text-base font-bold text-zinc-100 flex items-center space-x-2">
          <ShieldAlert className="h-5 w-5 text-red-400" />
          <span>Framework Security Controls Evaluation</span>
        </h3>
        <span className="text-xs text-zinc-400 font-mono">
          Showing {controls.length} controls
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-zinc-900/80 text-zinc-400 uppercase tracking-wider text-[10px] border-b border-zinc-800">
            <tr>
              <th className="px-6 py-3.5 font-bold">Control ID</th>
              <th className="px-6 py-3.5 font-bold">Control Title & Description</th>
              <th className="px-6 py-3.5 font-bold text-center">Status</th>
              <th className="px-6 py-3.5 font-bold text-center">Mapped Findings</th>
              <th className="px-6 py-3.5 font-bold text-right">Evidence Details</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/80">
            {controls.map((ctrl) => {
              const isPass = ctrl.status === "PASS";
              return (
                <tr
                  key={ctrl.control_id}
                  onClick={() => onSelectControl(ctrl)}
                  className="hover:bg-zinc-900/60 transition-colors cursor-pointer group"
                >
                  <td className="px-6 py-4 font-mono font-bold text-zinc-200 whitespace-nowrap">
                    {ctrl.control_id}
                  </td>
                  <td className="px-6 py-4 max-w-md">
                    <div className="font-semibold text-zinc-100 group-hover:text-red-400 transition-colors">
                      {ctrl.title}
                    </div>
                    <div className="text-[11px] text-zinc-400 line-clamp-2 mt-1">
                      {ctrl.description}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-center whitespace-nowrap">
                    {isPass ? (
                      <Badge variant="success" className="inline-flex items-center space-x-1">
                        <CheckCircle2 className="h-3 w-3 mr-1 text-emerald-400" />
                        <span>PASS</span>
                      </Badge>
                    ) : (
                      <Badge variant="critical" className="inline-flex items-center space-x-1">
                        <XCircle className="h-3 w-3 mr-1 text-red-400" />
                        <span>FAIL</span>
                      </Badge>
                    )}
                  </td>
                  <td className="px-6 py-4 text-center whitespace-nowrap font-mono font-semibold">
                    {ctrl.mapped_findings_count > 0 ? (
                      <span className="text-red-400 bg-red-950/40 border border-red-800/60 px-2.5 py-1 rounded-md">
                        {ctrl.mapped_findings_count} Open Findings
                      </span>
                    ) : (
                      <span className="text-emerald-400 bg-emerald-950/40 border border-emerald-800/60 px-2.5 py-1 rounded-md">
                        0 Findings
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-right whitespace-nowrap">
                    <button className="inline-flex items-center text-xs font-semibold text-zinc-400 hover:text-white transition-colors">
                      <span>View Traceability</span>
                      <ChevronRight className="h-4 w-4 ml-1 group-hover:translate-x-1 transition-transform" />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
