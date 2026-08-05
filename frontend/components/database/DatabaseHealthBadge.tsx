"use client";

import React from "react";
import { ShieldCheck, AlertTriangle, XCircle } from "lucide-react";

interface DatabaseHealthBadgeProps {
  status: "HEALTHY" | "WARNING" | "CRITICAL";
}

export const DatabaseHealthBadge: React.FC<DatabaseHealthBadgeProps> = ({ status }) => {
  switch (status) {
    case "HEALTHY":
      return (
        <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-emerald-950/60 border border-emerald-500/40 text-xs font-bold text-emerald-400">
          <ShieldCheck className="h-3.5 w-3.5" />
          <span>HEALTHY</span>
        </span>
      );
    case "WARNING":
      return (
        <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-amber-950/60 border border-amber-500/40 text-xs font-bold text-amber-400">
          <AlertTriangle className="h-3.5 w-3.5" />
          <span>WARNING</span>
        </span>
      );
    case "CRITICAL":
      return (
        <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-red-950/60 border border-red-500/40 text-xs font-bold text-red-400">
          <XCircle className="h-3.5 w-3.5" />
          <span>CRITICAL</span>
        </span>
      );
    default:
      return null;
  }
};
