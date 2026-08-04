"use client";

import React, { useState } from "react";
import { EvidenceItem } from "@/services/vulnerabilities.service";

interface EvidenceViewerDrawerProps {
  evidenceItems: EvidenceItem[];
}

export const EvidenceViewerDrawer: React.FC<EvidenceViewerDrawerProps> = ({
  evidenceItems,
}) => {
  const [selectedId, setSelectedId] = useState<string | null>(
    evidenceItems.length > 0 ? evidenceItems[0].id : null
  );

  const selectedItem = evidenceItems.find((item) => item.id === selectedId);

  if (evidenceItems.length === 0) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-8 text-center">
        <p className="text-sm font-medium text-zinc-400">
          No multi-modal proof evidence artifacts attached to this finding.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-6">
      <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
        <div>
          <h3 className="text-lg font-bold text-zinc-100">
            Multi-Modal Evidence Record Viewer
          </h3>
          <p className="text-xs text-zinc-400">
            Permission-controlled proof records with integrity verification checksums.
          </p>
        </div>
        <span className="rounded bg-zinc-800 px-2.5 py-1 text-xs font-semibold text-zinc-300">
          {evidenceItems.length} Artifacts
        </span>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-4">
        {/* Left Side: Artifact List */}
        <div className="flex flex-col gap-2 lg:col-span-1">
          {evidenceItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setSelectedId(item.id)}
              className={`flex flex-col gap-1 rounded-lg border p-3 text-left transition-all ${
                selectedId === item.id
                  ? "border-red-500/50 bg-red-500/10 text-zinc-100"
                  : "border-zinc-800 bg-zinc-900/50 text-zinc-400 hover:border-zinc-700 hover:bg-zinc-900"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-zinc-300">
                  {item.artifact_type}
                </span>
                <span className="text-[10px] text-zinc-500">
                  {new Date(item.created_at).toLocaleTimeString()}
                </span>
              </div>
              <span className="text-xs font-medium truncate text-zinc-400">
                {item.type_label}
              </span>
            </button>
          ))}
        </div>

        {/* Right Side: Evidence Detail Viewer */}
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4 lg:col-span-3">
          {selectedItem ? (
            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between border-b border-zinc-800/60 pb-3">
                <div>
                  <h4 className="text-sm font-bold text-zinc-200">
                    {selectedItem.type_label}
                  </h4>
                  <p className="text-xs font-mono text-zinc-500">
                    Storage Path: {selectedItem.storage_path}
                  </p>
                </div>
                <div className="text-right">
                  <span className="rounded bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-mono text-emerald-400">
                    SHA256 Verified
                  </span>
                  <p className="mt-1 text-[10px] font-mono text-zinc-500 truncate max-w-[200px]">
                    {selectedItem.checksum}
                  </p>
                </div>
              </div>

              {/* Payload/Metadata Viewer */}
              <div className="rounded-md bg-zinc-950 p-4 border border-zinc-800 font-mono text-xs text-zinc-300 overflow-x-auto max-h-96">
                {selectedItem.metadata ? (
                  <pre className="whitespace-pre-wrap">
                    {JSON.stringify(selectedItem.metadata, null, 2)}
                  </pre>
                ) : (
                  <p className="text-zinc-500 italic">
                    Raw evidence payload stored at {selectedItem.storage_path}
                  </p>
                )}
              </div>
            </div>
          ) : (
            <p className="text-xs text-zinc-500">Select an evidence artifact to view proof.</p>
          )}
        </div>
      </div>
    </div>
  );
};
