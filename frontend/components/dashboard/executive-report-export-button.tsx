"use client";

import * as React from "react";
import { Download, FileText, FileSpreadsheet } from "lucide-react";
import { Button } from "@/components/ui/button";

export function ExecutiveReportExportButton() {
  const handleExport = (format: "json" | "csv") => {
    window.open(`/api/v1/dashboard/export?format=${format}`, "_blank");
  };

  return (
    <div className="flex items-center space-x-2">
      <Button
        variant="outline"
        size="sm"
        onClick={() => handleExport("json")}
        className="text-xs font-mono"
      >
        <FileText className="mr-1.5 h-3.5 w-3.5 text-red-400" />
        <span>Export JSON</span>
      </Button>

      <Button
        variant="outline"
        size="sm"
        onClick={() => handleExport("csv")}
        className="text-xs font-mono"
      >
        <FileSpreadsheet className="mr-1.5 h-3.5 w-3.5 text-emerald-400" />
        <span>Export CSV</span>
      </Button>
    </div>
  );
}
