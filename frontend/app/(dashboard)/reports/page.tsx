"use client";

import React, { useEffect, useState } from "react";
import {
  FileText,
  Plus,
  BarChart3,
  Loader2,
  RefreshCw,
  Search,
  ShieldCheck,
} from "lucide-react";
import {
  ReportsService,
  ExecutiveReportMetadataResponse,
  CreateExecutiveReportRequest,
} from "@/services/reports.service";
import { ExecutiveReportCard } from "@/components/reports/ExecutiveReportCard";
import { ReportGenerationModal } from "@/components/reports/ReportGenerationModal";

export default function ReportsDashboardPage() {
  const [reports, setReports] = useState<ExecutiveReportMetadataResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  const loadInitialReport = async () => {
    try {
      setLoading(true);
      // Generate default current executive report summary item
      const payload = await ReportsService.generateExecutiveReport();
      setReports([payload.metadata]);
    } catch (err) {
      console.error("Failed to load executive report metadata:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInitialReport();
  }, []);

  const handleGenerateReport = async (req: CreateExecutiveReportRequest) => {
    const payload = await ReportsService.generateExecutiveReport(req);
    setReports((prev) => [payload.metadata, ...prev]);
  };

  const handleDownloadPdf = async (id: string) => {
    try {
      const blob = await ReportsService.downloadPdfReport(id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Vulnova_Executive_Report_${id.slice(0, 8)}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error("Failed to download PDF report:", err);
    }
  };

  const filteredReports = reports.filter((r) =>
    r.title.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-6 md:p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-2.5 mb-1">
            <div className="p-2 bg-sky-500/10 border border-sky-500/20 rounded-xl">
              <FileText className="w-6 h-6 text-sky-400" />
            </div>
            <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
              Executive Security Reports & Exports
            </h1>
          </div>
          <p className="text-sm text-slate-400">
            Generate presentation-ready CISO security posture reports, risk summaries, and PDF exports.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadInitialReport}
            className="inline-flex items-center gap-2 px-3.5 py-2.5 text-xs font-semibold rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-300 transition-colors"
          >
            <RefreshCw className="w-4 h-4 text-slate-400" />
            Refresh
          </button>

          <button
            onClick={() => setModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 text-xs font-bold rounded-xl bg-sky-600 hover:bg-sky-500 text-white shadow-lg shadow-sky-600/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            Generate Report
          </button>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between text-xs text-slate-400 font-semibold mb-2">
            <span>CISO PDF Generator</span>
            <FileText className="w-4 h-4 text-sky-400" />
          </div>
          <p className="text-xs text-slate-400">
            Jinja2 template engine rendering print-ready PDF documents via WeasyPrint.
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between text-xs text-slate-400 font-semibold mb-2">
            <span>Historical Posture Trajectory</span>
            <BarChart3 className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-xs text-slate-400">
            Time-series risk trajectory analytics over 7, 30, 90, or 365 days.
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between text-xs text-slate-400 font-semibold mb-2">
            <span>Compliance Standard Mappings</span>
            <ShieldCheck className="w-4 h-4 text-sky-400" />
          </div>
          <p className="text-xs text-slate-400">
            OWASP ASVS v4.0 and RFC 9116 security disclosure governance alignment.
          </p>
        </div>
      </div>

      {/* Reports List Controls */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search generated reports..."
            className="w-full pl-10 pr-4 py-2 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-sky-500 transition-colors"
          />
        </div>
        <span className="text-xs text-slate-500 font-medium">
          Showing {filteredReports.length} reports
        </span>
      </div>

      {/* Reports Grid */}
      {loading ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin text-sky-400 mx-auto mb-3" />
          <p className="text-sm font-semibold text-slate-300">
            Generating Executive Report Payload...
          </p>
        </div>
      ) : filteredReports.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {filteredReports.map((report) => (
            <ExecutiveReportCard
              key={report.id}
              report={report}
              onDownloadPdf={handleDownloadPdf}
            />
          ))}
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center text-slate-500">
          <FileText className="w-10 h-10 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No executive reports generated yet.</p>
        </div>
      )}

      {/* Report Generation Modal */}
      <ReportGenerationModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onGenerate={handleGenerateReport}
      />
    </div>
  );
}
