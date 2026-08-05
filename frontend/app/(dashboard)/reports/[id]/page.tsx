"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, FileText, Loader2 } from "lucide-react";
import {
  ReportsService,
  ExecutiveReportDataPayload,
} from "@/services/reports.service";
import { SecurityMetricsSummary } from "@/components/reports/SecurityMetricsSummary";
import { ReportPreview } from "@/components/reports/ReportPreview";
import { ReportDownloadActions } from "@/components/reports/ReportDownloadActions";

export default function ReportDetailPage() {
  const params = useParams();
  const reportId = params?.id as string;

  const [payload, setPayload] = useState<ExecutiveReportDataPayload | null>(null);
  const [htmlContent, setHtmlContent] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!reportId) return;

    const loadData = async () => {
      try {
        setLoading(true);
        const reportPayload = await ReportsService.generateExecutiveReport();
        const html = await ReportsService.getHtmlReport(reportId);
        setPayload(reportPayload);
        setHtmlContent(html);
      } catch (err) {
        console.error("Failed to load report detail:", err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [reportId]);

  if (loading || !payload) {
    return (
      <div className="p-8 text-center text-slate-400">
        <Loader2 className="w-8 h-8 animate-spin text-sky-400 mx-auto mb-3" />
        <p className="text-sm font-semibold text-slate-300">Loading Executive Security Report...</p>
      </div>
    );
  }

  return (
    <div className="p-6 md:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Navigation & Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <Link
            href="/reports"
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 mb-3 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Executive Reports
          </Link>
          <div className="flex items-center gap-2.5">
            <FileText className="w-6 h-6 text-sky-400" />
            <h1 className="text-xl font-bold text-slate-100">
              {payload.metadata.title}
            </h1>
          </div>
        </div>

        <ReportDownloadActions
          reportId={reportId}
          title={payload.metadata.title}
        />
      </div>

      {/* Metrics Summary Tiles */}
      <SecurityMetricsSummary
        metadata={payload.metadata}
        mttrHours={payload.historical_trends.mean_time_to_remediate_hours}
      />

      {/* HTML Report Live Preview Container */}
      <ReportPreview htmlContent={htmlContent} loading={false} />
    </div>
  );
}
