"use client";

import React, { useState } from "react";
import { ExternalLink, RefreshCw, Server, Github, CheckCircle2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ExternalIssueDTO, IntegrationsService } from "@/services/integrations.service";

interface IntegrationHistoryPanelProps {
  issues?: ExternalIssueDTO[];
  findingId?: string;
}

export const IntegrationHistoryPanel: React.FC<IntegrationHistoryPanelProps> = ({
  issues = [],
  findingId,
}) => {
  const [syncing, setSyncing] = useState<string | null>(null);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  const handleSync = async (issue: ExternalIssueDTO) => {
    if (!findingId) return;
    setSyncing(issue.issue_key);
    setSyncMessage(null);
    try {
      let res;
      if (issue.provider === "jira") {
        res = await IntegrationsService.syncJiraStatus(findingId, issue.issue_key);
      } else {
        res = await IntegrationsService.syncGitHubStatus(findingId, issue.issue_key.replace("#", ""));
      }
      setSyncMessage(
        `Synced ${issue.provider.toUpperCase()} status: ${res.external_status} -> Vulnova finding status: ${res.updated_vulnova_status}`
      );
    } catch (err: any) {
      setSyncMessage(err.message || "Failed to sync issue status");
    } finally {
      setSyncing(null);
    }
  };

  if (issues.length === 0) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-6 text-center text-xs text-zinc-500">
        No external Jira or GitHub tickets created for this finding yet.
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-950/80 p-6 space-y-4 shadow-xl">
      <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
        <h3 className="text-sm font-bold text-white flex items-center space-x-2">
          <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          <span>Synchronized External Tickets ({issues.length})</span>
        </h3>
      </div>

      {syncMessage && (
        <div className="p-3 rounded-lg border border-blue-900/60 bg-blue-950/20 text-xs text-blue-400">
          {syncMessage}
        </div>
      )}

      <div className="space-y-3">
        {issues.map((iss) => {
          const isJira = iss.provider === "jira";
          return (
            <div
              key={iss.issue_id}
              className="flex items-center justify-between p-3.5 rounded-lg border border-zinc-800 bg-zinc-900/60 text-xs"
            >
              <div className="flex items-center space-x-3">
                <div
                  className={`flex h-8 w-8 items-center justify-center rounded-lg border ${
                    isJira
                      ? "border-blue-800/60 bg-blue-950/40 text-blue-400"
                      : "border-purple-800/60 bg-purple-950/40 text-purple-400"
                  }`}
                >
                  {isJira ? <Server className="h-4 w-4" /> : <Github className="h-4 w-4" />}
                </div>
                <div>
                  <div className="font-mono font-bold text-zinc-200">
                    {iss.provider.toUpperCase()} {iss.issue_key}
                  </div>
                  <div className="text-[11px] text-zinc-400">
                    Status: <span className="text-emerald-400 font-semibold">{iss.status}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                {findingId && (
                  <button
                    onClick={() => handleSync(iss)}
                    disabled={syncing === iss.issue_key}
                    className="flex items-center space-x-1 px-2.5 py-1.5 rounded-md bg-zinc-800 text-zinc-300 hover:text-white transition-colors"
                  >
                    <RefreshCw className={`h-3.5 w-3.5 ${syncing === iss.issue_key ? "animate-spin text-blue-400" : ""}`} />
                    <span>Sync Status</span>
                  </button>
                )}

                <a
                  href={iss.issue_url}
                  target="_blank"
                  rel="noreferrer"
                  className="p-1.5 text-zinc-400 hover:text-white bg-zinc-800 rounded-md transition-colors"
                >
                  <ExternalLink className="h-4 w-4" />
                </a>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
