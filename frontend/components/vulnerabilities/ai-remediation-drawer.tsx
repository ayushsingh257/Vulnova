"use client";

import React, { useState } from "react";
import {
  FindingRemediationResponse,
  VulnerabilitiesService,
} from "@/services/vulnerabilities.service";

interface AIRemediationDrawerProps {
  findingId: string;
  remediationData: FindingRemediationResponse;
}

export const AIRemediationDrawer: React.FC<AIRemediationDrawerProps> = ({
  findingId,
  remediationData: initialData,
}) => {
  const [remediation, setRemediation] = useState<FindingRemediationResponse>(initialData);
  const [isGenerating, setIsGenerating] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  const handleGenerateAIFix = async () => {
    setIsGenerating(true);
    try {
      const updated = await VulnerabilitiesService.requestAIRemediation(findingId);
      setRemediation(updated);
    } catch (err) {
      console.error("AI Remediation generation failed:", err);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleCopyPatch = (code: string, idx: number) => {
    navigator.clipboard.writeText(code);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between border-b border-zinc-800 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="text-lg font-bold text-zinc-100">
              AI Security Remediation Drawer
            </h3>
            <span className="rounded bg-purple-500/10 border border-purple-500/20 px-2 py-0.5 text-[10px] font-semibold text-purple-400">
              Advisory Copilot
            </span>
          </div>
          <p className="text-xs text-zinc-400 mt-1">
            AI-synthesized root cause analysis, code patch suggestions, and verification checklists.
          </p>
        </div>

        <button
          onClick={handleGenerateAIFix}
          disabled={isGenerating}
          className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-red-600 to-red-700 px-4 py-2 text-xs font-semibold text-white shadow transition-all hover:from-red-500 hover:to-red-600 disabled:opacity-50"
        >
          {isGenerating ? (
            <>
              <div className="h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
              <span>Generating AI Fix...</span>
            </>
          ) : (
            <>
              <span>✨ Trigger AI Fix Recommendation</span>
            </>
          )}
        </button>
      </div>

      <div className="mt-6 flex flex-col gap-6">
        {/* Explanation Summary */}
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-400">
            Root Cause & Impact Summary
          </h4>
          <p className="mt-2 text-sm text-zinc-200 leading-relaxed">
            {remediation.summary}
          </p>
          <p className="mt-2 text-xs text-zinc-400">
            {remediation.explanation}
          </p>
        </div>

        {/* Remediation Steps */}
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-3">
            Recommended Step-by-Step Fixes
          </h4>
          <div className="grid grid-cols-1 gap-3">
            {remediation.steps.map((step) => (
              <div
                key={step.sequence_number}
                className="flex items-start gap-3 rounded-lg border border-zinc-800 bg-zinc-900/30 p-3.5"
              >
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-zinc-800 text-xs font-bold text-red-400">
                  {step.sequence_number}
                </div>
                <div>
                  <h5 className="text-xs font-bold text-zinc-200">
                    {step.title}
                  </h5>
                  <p className="mt-1 text-xs text-zinc-400">
                    {step.description}
                  </p>
                  <span className="mt-2 inline-block text-[10px] text-zinc-500 font-mono">
                    Est. Effort: {step.estimated_minutes} minutes
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Patch Suggestions */}
        {remediation.patch_suggestions.length > 0 && (
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-3">
              Secure Code Patch Suggestions
            </h4>
            <div className="flex flex-col gap-4">
              {remediation.patch_suggestions.map((patch, idx) => (
                <div
                  key={idx}
                  className="rounded-lg border border-zinc-800 bg-zinc-950 overflow-hidden"
                >
                  <div className="flex items-center justify-between bg-zinc-900 px-4 py-2 border-b border-zinc-800">
                    <span className="text-xs font-mono text-zinc-300">
                      {patch.file_path || `patch_${idx + 1}.${patch.language}`}
                    </span>
                    <button
                      onClick={() => handleCopyPatch(patch.patch_code, idx)}
                      className="text-[10px] font-semibold text-zinc-400 hover:text-zinc-200"
                    >
                      {copiedIndex === idx ? "Copied!" : "Copy Code"}
                    </button>
                  </div>
                  <pre className="p-4 font-mono text-xs text-emerald-400 overflow-x-auto bg-zinc-950/90">
                    {patch.patch_code}
                  </pre>
                  {patch.explanation && (
                    <div className="p-3 bg-zinc-900/60 border-t border-zinc-800/60 text-xs text-zinc-400">
                      {patch.explanation}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Verification Checklist */}
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/30 p-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-zinc-400 mb-2">
            Verification & Quality Checklist
          </h4>
          <ul className="flex flex-col gap-1.5 text-xs text-zinc-300">
            {remediation.verification_steps.map((vStep, vIdx) => (
              <li key={vIdx} className="flex items-center gap-2">
                <span className="text-emerald-400 font-bold">✓</span>
                <span>{vStep}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};
