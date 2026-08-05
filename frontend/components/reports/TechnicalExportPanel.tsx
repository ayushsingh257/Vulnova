"use client";

import React, { useState } from "react";
import {
  Download,
  Code2,
  FileText,
  Table,
  Copy,
  Check,
} from "lucide-react";
import { ExportFormat, ExportService } from "@/services/export.service";

interface TechnicalExportPanelProps {
  findingId?: string; // Optional finding ID for single finding export mode
  title?: string;
}

export const TechnicalExportPanel: React.FC<TechnicalExportPanelProps> = ({
  findingId,
  title = "Developer Technical Remediation Export",
}) => {
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>("markdown");
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [isCopied, setIsCopied] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleDownload = async () => {
    setIsExporting(true);
    setErrorMessage(null);
    try {
      if (findingId) {
        await ExportService.downloadSingleFindingExport(findingId, selectedFormat);
      } else {
        await ExportService.downloadBulkExport(selectedFormat);
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to generate export download");
    } finally {
      setIsExporting(false);
    }
  };

  const handleCopyMarkdown = async () => {
    if (!findingId) return;
    setIsExporting(true);
    setErrorMessage(null);
    try {
      const mdContent = await ExportService.fetchSingleFindingMarkdown(findingId);
      await navigator.clipboard.writeText(mdContent);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2500);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to copy Markdown preview");
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className="p-2 bg-indigo-500/10 rounded-lg text-indigo-400">
            <Code2 className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">{title}</h3>
            <p className="text-xs text-slate-400">
              Export technical vulnerability intelligence, evidence dumps, attack chains, and AI remediation packages.
            </p>
          </div>
        </div>
      </div>

      {errorMessage && (
        <div className="mb-4 p-3 bg-red-950/50 border border-red-800/50 rounded-lg text-red-300 text-sm">
          {errorMessage}
        </div>
      )}

      {/* Format Selection Tabs */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <button
          type="button"
          onClick={() => setSelectedFormat("markdown")}
          className={`flex items-center justify-center space-x-2 py-3 px-4 rounded-lg border text-sm font-medium transition-all ${
            selectedFormat === "markdown"
              ? "bg-indigo-600/20 border-indigo-500 text-indigo-300 shadow-md"
              : "bg-slate-800/50 border-slate-700/50 text-slate-400 hover:text-white hover:bg-slate-800"
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>Markdown (Ticket)</span>
        </button>

        <button
          type="button"
          onClick={() => setSelectedFormat("json")}
          className={`flex items-center justify-center space-x-2 py-3 px-4 rounded-lg border text-sm font-medium transition-all ${
            selectedFormat === "json"
              ? "bg-indigo-600/20 border-indigo-500 text-indigo-300 shadow-md"
              : "bg-slate-800/50 border-slate-700/50 text-slate-400 hover:text-white hover:bg-slate-800"
          }`}
        >
          <Code2 className="w-4 h-4" />
          <span>JSON (Machine)</span>
        </button>

        <button
          type="button"
          onClick={() => setSelectedFormat("csv")}
          className={`flex items-center justify-center space-x-2 py-3 px-4 rounded-lg border text-sm font-medium transition-all ${
            selectedFormat === "csv"
              ? "bg-indigo-600/20 border-indigo-500 text-indigo-300 shadow-md"
              : "bg-slate-800/50 border-slate-700/50 text-slate-400 hover:text-white hover:bg-slate-800"
          }`}
        >
          <Table className="w-4 h-4" />
          <span>CSV (Spreadsheet)</span>
        </button>
      </div>

      {/* Export Action Controls */}
      <div className="flex items-center space-x-3">
        <button
          type="button"
          onClick={handleDownload}
          disabled={isExporting}
          className="flex-1 inline-flex items-center justify-center space-x-2 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg shadow transition-all"
        >
          <Download className="w-4 h-4" />
          <span>
            {isExporting
              ? "Generating Export..."
              : `Download ${selectedFormat.toUpperCase()} Export`}
          </span>
        </button>

        {findingId && selectedFormat === "markdown" && (
          <button
            type="button"
            onClick={handleCopyMarkdown}
            disabled={isExporting}
            className="inline-flex items-center space-x-2 py-2.5 px-4 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-200 text-sm font-medium rounded-lg border border-slate-700 transition-all"
            title="Copy Markdown ticket description to clipboard"
          >
            {isCopied ? (
              <>
                <Check className="w-4 h-4 text-emerald-400" />
                <span className="text-emerald-400">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-4 h-4 text-slate-400" />
                <span>Copy Ticket MD</span>
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
};
