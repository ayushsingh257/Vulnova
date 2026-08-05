"use client";

import React from "react";
import { RegressionCategoryResultDTO } from "@/services/regression_validation.service";
import { X, Wrench, AlertTriangle, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface RegressionDetailsModalProps {
  category: RegressionCategoryResultDTO | null;
  onClose: () => void;
}

export const RegressionDetailsModal: React.FC<RegressionDetailsModalProps> = ({
  category,
  onClose,
}) => {
  if (!category) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-xl bg-zinc-950 border-l border-zinc-800 h-full overflow-y-auto p-6 space-y-6 flex flex-col justify-between">
        <div className="space-y-6">
          {/* Header */}
          <div className="flex items-start justify-between border-b border-zinc-800 pb-4">
            <div>
              <div className="flex items-center space-x-2 mb-1">
                <span className="text-xs font-mono font-bold text-teal-400 bg-teal-950/50 border border-teal-800/40 px-2 py-0.5 rounded">
                  {category.category_code}
                </span>
                <Badge variant={category.status === "PASSED" ? "success" : category.status === "WARNING" ? "warning" : "critical"}>
                  {category.status}
                </Badge>
              </div>
              <h2 className="text-lg font-bold text-white">
                {category.category_name}
              </h2>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded text-zinc-400 hover:text-white hover:bg-zinc-900"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Diagnostic Failure / Warning Banner */}
          {category.failure_reason && (
            <div className="p-4 rounded-lg bg-amber-950/30 border border-amber-800/50 space-y-1">
              <div className="flex items-center space-x-2 font-bold text-amber-300 text-xs">
                <AlertTriangle className="h-4 w-4 text-amber-400" />
                <span>Security Regression Diagnostic</span>
              </div>
              <p className="text-xs text-zinc-300">
                {category.failure_reason}
              </p>
            </div>
          )}

          {/* Affected Architectural Component */}
          <div className="space-y-1.5">
            <span className="text-xs font-bold text-zinc-400 flex items-center space-x-1 uppercase tracking-wider">
              <ShieldCheck className="h-3.5 w-3.5 text-teal-400" />
              <span>Evaluated Platform Security Area</span>
            </span>
            <div className="p-3 rounded-lg bg-zinc-900 border border-zinc-800 text-xs font-mono text-teal-300">
              {category.affected_component || "Security Layer"}
            </div>
          </div>

          {/* Assertions Breakdown */}
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="p-3 rounded-lg bg-zinc-900 border border-zinc-800">
              <span className="text-xl font-bold text-white block">{category.total_assertions}</span>
              <span className="text-[11px] text-zinc-400">Total Guards</span>
            </div>
            <div className="p-3 rounded-lg bg-zinc-900 border border-zinc-800">
              <span className="text-xl font-bold text-emerald-400 block">{category.passed_assertions}</span>
              <span className="text-[11px] text-zinc-400">Passed</span>
            </div>
            <div className="p-3 rounded-lg bg-zinc-900 border border-zinc-800">
              <span className="text-xl font-bold text-red-400 block">{category.failed_assertions}</span>
              <span className="text-[11px] text-zinc-400">Failed</span>
            </div>
          </div>

          {/* Actionable Technical Remediation Guidance */}
          <div className="space-y-2">
            <div className="flex items-center space-x-2 text-xs font-bold text-white uppercase tracking-wider">
              <Wrench className="h-4 w-4 text-teal-400" />
              <span>Recommended Security Remediation</span>
            </div>
            <div className="p-4 rounded-lg bg-zinc-900/80 border border-zinc-800 text-xs text-zinc-300 leading-relaxed font-mono">
              {category.remediation_guidance}
            </div>
          </div>
        </div>

        <button
          onClick={onClose}
          className="w-full py-2 rounded-lg bg-zinc-900 border border-zinc-800 text-xs font-bold text-zinc-300 hover:text-white"
        >
          Close Detail View
        </button>
      </div>
    </div>
  );
};
