"use client";

import React from "react";
import { OWASPCategoryResultDTO } from "@/services/owasp_validation.service";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, AlertTriangle, XCircle, Info } from "lucide-react";

interface OWASPCategoryGridProps {
  categories: OWASPCategoryResultDTO[];
  onSelectCategory: (cat: OWASPCategoryResultDTO) => void;
}

export const OWASPCategoryGrid: React.FC<OWASPCategoryGridProps> = ({
  categories,
  onSelectCategory,
}) => {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case "PASSED":
        return <CheckCircle2 className="h-4 w-4 text-emerald-400" />;
      case "WARNING":
        return <AlertTriangle className="h-4 w-4 text-amber-400" />;
      default:
        return <XCircle className="h-4 w-4 text-red-400" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "PASSED":
        return <Badge variant="success">PASSED</Badge>;
      case "WARNING":
        return <Badge variant="warning">WARNING</Badge>;
      default:
        return <Badge variant="critical">FAILED</Badge>;
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {categories.map((cat) => (
        <div
          key={cat.category_code}
          onClick={() => onSelectCategory(cat)}
          className="group relative p-4 rounded-xl border border-zinc-800 bg-zinc-950/80 hover:border-purple-500/50 hover:bg-zinc-900/60 transition-all cursor-pointer space-y-3"
        >
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <div className="flex items-center space-x-2">
                <span className="text-xs font-mono font-bold text-purple-400 bg-purple-950/50 border border-purple-800/40 px-2 py-0.5 rounded">
                  {cat.category_code}
                </span>
                {getStatusBadge(cat.status)}
              </div>
              <h3 className="text-sm font-bold text-white group-hover:text-purple-300 transition-colors">
                {cat.category_name}
              </h3>
            </div>
            {getStatusIcon(cat.status)}
          </div>

          {/* Subsystem & Findings Metric */}
          <div className="flex items-center justify-between text-xs text-zinc-400">
            <span className="font-mono text-[11px] truncate max-w-[200px]">
              Subsystem: {cat.affected_subsystem || "Core Security Controls"}
            </span>
            <span className="font-semibold text-zinc-300">
              {cat.finding_count} {cat.finding_count === 1 ? "finding" : "findings"}
            </span>
          </div>

          {/* Progress bar */}
          <div className="space-y-1">
            <div className="flex justify-between text-[11px] text-zinc-400 font-mono">
              <span>Pass Rate</span>
              <span>{cat.pass_rate_percentage}%</span>
            </div>
            <div className="h-1.5 w-full bg-zinc-900 rounded-full overflow-hidden border border-zinc-800">
              <div
                className={`h-full transition-all ${
                  cat.status === "PASSED"
                    ? "bg-emerald-500"
                    : cat.status === "WARNING"
                    ? "bg-amber-500"
                    : "bg-red-500"
                }`}
                style={{ width: `${cat.pass_rate_percentage}%` }}
              />
            </div>
          </div>

          {/* Explanation Banner on Failure/Warning */}
          {cat.failure_reason && (
            <div className="p-2 rounded bg-zinc-900 border border-zinc-800 text-[11px] text-amber-300/90 flex items-start space-x-1.5">
              <Info className="h-3.5 w-3.5 text-amber-400 mt-0.5 shrink-0" />
              <span className="line-clamp-2">{cat.failure_reason}</span>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
