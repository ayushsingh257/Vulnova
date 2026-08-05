"use client";

import React from "react";
import { Eye, FileCode } from "lucide-react";

interface ReportPreviewProps {
  htmlContent: string;
  loading?: boolean;
}

export function ReportPreview({ htmlContent, loading }: ReportPreviewProps) {
  if (loading) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-slate-400">
        <div className="animate-spin w-8 h-8 border-2 border-sky-400 border-t-transparent rounded-full mx-auto mb-3" />
        <p className="text-sm font-semibold text-slate-300">Rendering HTML Report Preview...</p>
      </div>
    );
  }

  if (!htmlContent) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-12 text-center text-slate-500">
        <FileCode className="w-10 h-10 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No report preview content available.</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
      <div className="flex items-center justify-between px-5 py-3 bg-slate-950 border-b border-slate-800 text-xs font-semibold text-slate-400">
        <div className="flex items-center gap-2">
          <Eye className="w-4 h-4 text-sky-400" />
          <span>Executive Report HTML Live Preview</span>
        </div>
        <span className="text-[10px] text-slate-500 uppercase tracking-wider">
          Stand-alone Document Container
        </span>
      </div>

      <div className="p-2 bg-slate-950">
        <iframe
          srcDoc={htmlContent}
          title="Executive Report HTML Preview"
          className="w-full h-[650px] bg-white rounded-lg border border-slate-800"
          sandbox="allow-same-origin"
        />
      </div>
    </div>
  );
}
