"use client";

import React, { useState } from "react";
import { X, FileText, Loader2, Calendar } from "lucide-react";
import { CreateExecutiveReportRequest } from "@/services/reports.service";

interface ReportGenerationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onGenerate: (req: CreateExecutiveReportRequest) => Promise<void>;
}

export function ReportGenerationModal({
  isOpen,
  onClose,
  onGenerate,
}: ReportGenerationModalProps) {
  const [title, setTitle] = useState("CISO Executive Security Posture Report");
  const [timeframeDays, setTimeframeDays] = useState(30);
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      await onGenerate({
        title: title.trim() || "CISO Executive Security Posture Report",
        timeframe_days: timeframeDays,
      });
      onClose();
    } catch (err) {
      console.error("Failed to generate report:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-sky-400" />
            <h2 className="text-base font-bold text-slate-100">
              Generate Executive Security Report
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Report Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Q3 Enterprise Security Posture Report"
              className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-sky-500 transition-colors"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Analysis Window Timeframe
            </label>
            <div className="grid grid-cols-4 gap-2">
              {[7, 30, 90, 365].map((days) => (
                <button
                  key={days}
                  type="button"
                  onClick={() => setTimeframeDays(days)}
                  className={`flex flex-col items-center justify-center p-3 rounded-xl border text-xs font-bold transition-all ${
                    timeframeDays === days
                      ? "bg-sky-500/20 border-sky-500 text-sky-400"
                      : "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200"
                  }`}
                >
                  <Calendar className="w-4 h-4 mb-1" />
                  <span>{days} Days</span>
                </button>
              ))}
            </div>
          </div>

          <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 text-xs text-slate-400 space-y-1">
            <span className="font-semibold text-slate-300">Report Scope Included:</span>
            <ul className="list-disc list-inside space-y-0.5 text-slate-400">
              <li>Executive Security Posture Score & Status</li>
              <li>Risk Velocity & Historical Trajectory Analytics</li>
              <li>Priority Vulnerability Intelligence Breakdown</li>
              <li>Attack Surface Environment Coverage</li>
              <li>Threat Advisories & Compliance Standard Mappings</li>
            </ul>
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 text-xs font-semibold rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center gap-2 px-5 py-2.5 text-xs font-bold rounded-xl bg-sky-600 hover:bg-sky-500 text-white shadow-lg shadow-sky-600/20 transition-all disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <FileText className="w-4 h-4" />
                  Generate Report Payload
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
