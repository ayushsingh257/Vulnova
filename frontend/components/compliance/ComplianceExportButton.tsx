"use client";

import React, { useState } from "react";
import { Download, Loader2 } from "lucide-react";
import { ComplianceService } from "@/services/compliance.service";

interface ComplianceExportButtonProps {
  framework: string;
}

export const ComplianceExportButton: React.FC<ComplianceExportButtonProps> = ({
  framework,
}) => {
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExport = async () => {
    setIsExporting(true);
    setError(null);
    try {
      await ComplianceService.exportComplianceReport(framework);
    } catch (err: any) {
      setError(err.message || "Failed to export compliance report");
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="inline-flex flex-col items-end">
      <button
        onClick={handleExport}
        disabled={isExporting}
        className="flex items-center space-x-2 rounded-xl bg-red-600/20 border border-red-500/40 px-4 py-2 text-xs font-semibold text-red-400 hover:bg-red-600/30 hover:text-white transition-all shadow-md shadow-red-950/40 disabled:opacity-50"
      >
        {isExporting ? (
          <Loader2 className="h-4 w-4 animate-spin text-red-400" />
        ) : (
          <Download className="h-4 w-4 text-red-400" />
        )}
        <span>{isExporting ? "Generating Report..." : "Export Compliance Report"}</span>
      </button>
      {error && <p className="text-[11px] text-red-400 mt-1">{error}</p>}
    </div>
  );
};
