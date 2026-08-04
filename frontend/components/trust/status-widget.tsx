"use client";

import * as React from "react";
import { CheckCircle2, AlertTriangle, Wrench } from "lucide-react";

export interface StatusWidgetProps {
  status?: "OPERATIONAL" | "DEGRADED" | "MAINTENANCE" | string;
}

export function StatusWidget({ status = "OPERATIONAL" }: StatusWidgetProps) {
  const getStatusConfig = (s: string) => {
    switch (s.toUpperCase()) {
      case "DEGRADED":
      case "DEGRADED_PERFORMANCE":
        return {
          label: "DEGRADED PERFORMANCE",
          badgeClass: "border-amber-900/60 bg-amber-950/40 text-amber-400",
          icon: <AlertTriangle className="h-3.5 w-3.5 text-amber-400 animate-pulse" />,
        };
      case "MAINTENANCE":
      case "UNDER_MAINTENANCE":
        return {
          label: "UNDER MAINTENANCE",
          badgeClass: "border-blue-900/60 bg-blue-950/40 text-blue-400",
          icon: <Wrench className="h-3.5 w-3.5 text-blue-400" />,
        };
      default:
        return {
          label: "SYSTEMS OPERATIONAL",
          badgeClass: "border-emerald-900/60 bg-emerald-950/40 text-emerald-400",
          icon: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />,
        };
    }
  };

  const config = getStatusConfig(status);

  return (
    <div
      className={`inline-flex items-center space-x-2 rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-wider ${config.badgeClass}`}
    >
      {config.icon}
      <span className="font-mono text-[11px]">{config.label}</span>
    </div>
  );
}
