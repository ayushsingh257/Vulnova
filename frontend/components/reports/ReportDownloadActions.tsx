"use client";

import React, { useState } from "react";
import { Download, FileText, Code, Table, Loader2 } from "lucide-react";
import { ReportsService } from "@/services/reports.service";

interface ReportDownloadActionsProps {
  reportId: string;
  title?: string;
  onDownloadJson?: () => void;
  onDownloadCsv?: () => void;
}

export function ReportDownloadActions({
  reportId,
  title = "Executive Report",
  onDownloadJson,
  onDownloadCsv,
}: ReportDownloadActionsProps) {
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  const handleDownloadPdf = async () => {
    try {
      setDownloadingPdf(true);
      const blob = await ReportsService.downloadPdfReport(reportId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Vulnova_Executive_Report_${reportId.slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error("PDF Download error:", err);
    } finally {
      setDownloadingPdf(false);
    }
  };

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={handleDownloadPdf}
        disabled={downloadingPdf}
        className="inline-flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-xl bg-sky-600 hover:bg-sky-500 text-white shadow-lg shadow-sky-600/20 transition-all disabled:opacity-50"
      >
        {downloadingPdf ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Downloading PDF...
          </>
        ) : (
          <>
            <Download className="w-4 h-4" />
            Download PDF
          </>
        )}
      </button>

      {onDownloadJson && (
        <button
          onClick={onDownloadJson}
          className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
        >
          <Code className="w-3.5 h-3.5" />
          JSON
        </button>
      )}

      {onDownloadCsv && (
        <button
          onClick={onDownloadCsv}
          className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
        >
          <Table className="w-3.5 h-3.5" />
          CSV
        </button>
      )}
    </div>
  );
}
