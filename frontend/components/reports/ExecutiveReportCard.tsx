"use client";

import React from "react";
import Link from "next/link";
import { FileText, Calendar, Shield, ExternalLink, Download } from "lucide-react";
import { ExecutiveReportMetadataResponse } from "@/services/reports.service";

interface ExecutiveReportCardProps {
  report: ExecutiveReportMetadataResponse;
  onDownloadPdf?: (id: string) => void;
}

export function ExecutiveReportCard({
  report,
  onDownloadPdf,
}: ExecutiveReportCardProps) {
  const isSecure = report.posture_status === "SECURE";
  const isElevated = report.posture_status === "ELEVATED_RISK";

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-all flex flex-col justify-between">
      <div>
        <div className="flex items-start justify-between mb-3">
          <div className="p-2.5 bg-sky-500/10 border border-sky-500/20 rounded-lg">
            <FileText className="w-5 h-5 text-sky-400" />
          </div>
          <span
            className={`text-xs px-2.5 py-0.5 rounded-full font-bold uppercase ${
              isSecure
                ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                : isElevated
                ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                : "bg-red-500/20 text-red-400 border border-red-500/30"
            }`}
          >
            {report.posture_status.replace("_", " ")}
          </span>
        </div>

        <h3 className="text-base font-bold text-slate-100 mb-1 line-clamp-1">
          {report.title}
        </h3>

        <div className="flex items-center text-xs text-slate-400 gap-3 mb-4">
          <span className="flex items-center gap-1">
            <Calendar className="w-3.5 h-3.5 text-slate-500" />
            {new Date(report.generated_at).toLocaleDateString()}
          </span>
          <span className="flex items-center gap-1">
            <Shield className="w-3.5 h-3.5 text-sky-400" />
            Score: {report.posture_score.toFixed(1)}
          </span>
        </div>

        <div className="grid grid-cols-3 gap-2 bg-slate-950/60 p-2.5 rounded-lg text-center text-xs mb-4">
          <div>
            <div className="text-slate-500 text-[10px] uppercase font-semibold">Total</div>
            <div className="font-bold text-slate-200">{report.total_findings}</div>
          </div>
          <div>
            <div className="text-slate-500 text-[10px] uppercase font-semibold">Critical</div>
            <div className="font-bold text-rose-400">{report.critical_findings}</div>
          </div>
          <div>
            <div className="text-slate-500 text-[10px] uppercase font-semibold">High</div>
            <div className="font-bold text-amber-400">{report.high_findings}</div>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 pt-2 border-t border-slate-800">
        <Link
          href={`/reports/${report.id}`}
          className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          View Report
        </Link>

        {onDownloadPdf && (
          <button
            onClick={() => onDownloadPdf(report.id)}
            className="inline-flex items-center justify-center p-2 rounded-lg bg-sky-600/20 hover:bg-sky-600/30 text-sky-400 border border-sky-500/30 transition-colors"
            title="Download PDF Document"
          >
            <Download className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}
