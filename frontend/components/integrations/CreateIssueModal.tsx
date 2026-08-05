"use client";

import React, { useState } from "react";
import { X, Server, Github, ExternalLink, Loader2 } from "lucide-react";
import {
  ExternalIssueDTO,
  IntegrationsService,
} from "@/services/integrations.service";

interface CreateIssueModalProps {
  findingId: string;
  findingTitle: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (issue: ExternalIssueDTO) => void;
}

export const CreateIssueModal: React.FC<CreateIssueModalProps> = ({
  findingId,
  findingTitle,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [provider, setProvider] = useState<"jira" | "github">("jira");
  const [labelsStr, setLabelsStr] = useState<string>("sec-p1, urgent");
  const [creating, setCreating] = useState(false);
  const [result, setResult] = useState<ExternalIssueDTO | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError(null);
    setResult(null);

    const labels = labelsStr
      .split(",")
      .map((l) => l.trim())
      .filter((l) => l.length > 0);

    try {
      let res: ExternalIssueDTO;
      if (provider === "jira") {
        res = await IntegrationsService.createJiraIssue(findingId, {
          custom_labels: labels,
        });
      } else {
        res = await IntegrationsService.createGitHubIssue(findingId, {
          custom_labels: labels,
        });
      }
      setResult(res);
      if (onSuccess) onSuccess(res);
    } catch (err: any) {
      setError(err.message || "Failed to create external ticket");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg bg-zinc-950 border border-zinc-800 rounded-xl p-6 space-y-4 shadow-2xl">
        <div className="flex justify-between items-center border-b border-zinc-800 pb-3">
          <div>
            <h3 className="text-base font-bold text-white">Create External Ticket</h3>
            <p className="text-xs text-zinc-400 truncate max-w-sm mt-0.5">{findingTitle}</p>
          </div>
          <button onClick={onClose} className="text-zinc-400 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        {result ? (
          <div className="space-y-4 text-center py-4">
            <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-emerald-950 border border-emerald-800 text-emerald-400">
              ✓
            </div>
            <div>
              <h4 className="text-sm font-bold text-white">External Ticket Created!</h4>
              <p className="text-xs text-zinc-400 mt-1">
                {result.provider.toUpperCase()} Issue Key:{" "}
                <span className="font-mono text-emerald-400 font-bold">{result.issue_key}</span>
              </p>
            </div>
            <a
              href={result.issue_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center space-x-2 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-semibold text-white hover:bg-emerald-500 transition-colors"
            >
              <span>Open in {result.provider.toUpperCase()}</span>
              <ExternalLink className="h-4 w-4" />
            </a>
          </div>
        ) : (
          <form onSubmit={handleCreate} className="space-y-4 text-xs">
            <div>
              <label className="block text-zinc-400 mb-1.5 font-medium">Select Integration Provider</label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setProvider("jira")}
                  className={`flex items-center justify-center space-x-2 p-3 rounded-lg border text-xs font-semibold transition-all ${
                    provider === "jira"
                      ? "border-blue-500 bg-blue-950/40 text-blue-400 shadow-md shadow-blue-950/40"
                      : "border-zinc-800 bg-zinc-900 text-zinc-400 hover:border-zinc-700"
                  }`}
                >
                  <Server className="h-4 w-4" />
                  <span>Jira Cloud</span>
                </button>
                <button
                  type="button"
                  onClick={() => setProvider("github")}
                  className={`flex items-center justify-center space-x-2 p-3 rounded-lg border text-xs font-semibold transition-all ${
                    provider === "github"
                      ? "border-purple-500 bg-purple-950/40 text-purple-400 shadow-md shadow-purple-950/40"
                      : "border-zinc-800 bg-zinc-900 text-zinc-400 hover:border-zinc-700"
                  }`}
                >
                  <Github className="h-4 w-4" />
                  <span>GitHub Issues</span>
                </button>
              </div>
            </div>

            <div>
              <label className="block text-zinc-400 mb-1">Issue Labels (comma separated)</label>
              <input
                type="text"
                value={labelsStr}
                onChange={(e) => setLabelsStr(e.target.value)}
                className="w-full rounded-md border border-zinc-800 bg-zinc-900 p-2 text-zinc-200"
              />
            </div>

            {error && <p className="text-red-400 text-[11px]">{error}</p>}

            <div className="flex justify-end space-x-2 pt-2 border-t border-zinc-800">
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-1.5 rounded-md bg-zinc-800 text-zinc-300"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={creating}
                className="flex items-center space-x-2 px-4 py-1.5 rounded-md bg-red-600 text-white font-semibold hover:bg-red-500 transition-colors"
              >
                {creating ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin text-white" />
                    <span>Creating Ticket...</span>
                  </>
                ) : (
                  <span>Create Ticket</span>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
