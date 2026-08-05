"use client";

import React, { useState } from "react";
import { Lock, ShieldCheck, CheckCircle2, AlertCircle, Key, Server, Github } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  IntegrationConfigResponse,
  IntegrationsService,
  SaveJiraConfigRequest,
  SaveGitHubConfigRequest,
} from "@/services/integrations.service";

interface IntegrationSettingsCardProps {
  config: IntegrationConfigResponse;
  onRefresh: () => void;
}

export const IntegrationSettingsCard: React.FC<IntegrationSettingsCardProps> = ({
  config,
  onRefresh,
}) => {
  const [showJiraModal, setShowJiraModal] = useState(false);
  const [showGitHubModal, setShowGitHubModal] = useState(false);

  const [jiraForm, setJiraForm] = useState<SaveJiraConfigRequest>({
    host_url: config.jira.host_url || "",
    email: config.jira.email || "",
    api_token: "",
    project_key: config.jira.project_key || "",
    issue_type: config.jira.issue_type || "Bug",
  });

  const [githubForm, setGithubForm] = useState<SaveGitHubConfigRequest>({
    repo_owner: config.github.repo_owner || "",
    repo_name: config.github.repo_name || "",
    personal_access_token: "",
  });

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSaveJira = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await IntegrationsService.saveJiraConfig(jiraForm);
      setShowJiraModal(false);
      onRefresh();
    } catch (err: any) {
      setError(err.message || "Failed to save Jira configuration");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveGitHub = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await IntegrationsService.saveGitHubConfig(githubForm);
      setShowGitHubModal(false);
      onRefresh();
    } catch (err: any) {
      setError(err.message || "Failed to save GitHub configuration");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Jira Cloud Card */}
      <Card className="border-zinc-800 bg-zinc-950/80 backdrop-blur-md">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <div className="flex items-center space-x-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-950/50 border border-blue-800/60 text-blue-400">
              <Server className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-base font-bold text-white">Jira Cloud Integration</CardTitle>
              <p className="text-xs text-zinc-400">Atlassian REST API v3</p>
            </div>
          </div>
          <Badge variant={config.jira.is_configured ? "success" : "default"}>
            {config.jira.is_configured ? "CONNECTED" : "NOT CONFIGURED"}
          </Badge>
        </CardHeader>
        <CardContent className="pt-4 space-y-4">
          <div className="space-y-2 text-xs font-mono bg-zinc-900/60 p-3 rounded-lg border border-zinc-800">
            <div className="flex justify-between">
              <span className="text-zinc-500">Host URL:</span>
              <span className="text-zinc-200 font-semibold">{config.jira.host_url || "Not configured"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">Project Key:</span>
              <span className="text-blue-400 font-semibold">{config.jira.project_key || "N/A"}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">API Token:</span>
              <span className="text-zinc-400">{config.jira.api_token_masked || "Scrubbed / Encrypted"}</span>
            </div>
          </div>

          <button
            onClick={() => setShowJiraModal(true)}
            className="w-full rounded-lg bg-zinc-900 border border-zinc-800 px-4 py-2 text-xs font-semibold text-zinc-200 hover:bg-zinc-800 hover:text-white transition-colors"
          >
            {config.jira.is_configured ? "Configure Jira Settings" : "Connect Jira Cloud"}
          </button>
        </CardContent>
      </Card>

      {/* GitHub Issues Card */}
      <Card className="border-zinc-800 bg-zinc-950/80 backdrop-blur-md">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <div className="flex items-center space-x-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-950/50 border border-purple-800/60 text-purple-400">
              <Github className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-base font-bold text-white">GitHub Issues Integration</CardTitle>
              <p className="text-xs text-zinc-400">GitHub REST API v3</p>
            </div>
          </div>
          <Badge variant={config.github.is_configured ? "success" : "default"}>
            {config.github.is_configured ? "CONNECTED" : "NOT CONFIGURED"}
          </Badge>
        </CardHeader>
        <CardContent className="pt-4 space-y-4">
          <div className="space-y-2 text-xs font-mono bg-zinc-900/60 p-3 rounded-lg border border-zinc-800">
            <div className="flex justify-between">
              <span className="text-zinc-500">Target Repo:</span>
              <span className="text-purple-400 font-semibold">
                {config.github.repo_owner && config.github.repo_name
                  ? `${config.github.repo_owner}/${config.github.repo_name}`
                  : "Not configured"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-zinc-500">Access Token:</span>
              <span className="text-zinc-400">{config.github.personal_access_token_masked || "Scrubbed / Encrypted"}</span>
            </div>
          </div>

          <button
            onClick={() => setShowGitHubModal(true)}
            className="w-full rounded-lg bg-zinc-900 border border-zinc-800 px-4 py-2 text-xs font-semibold text-zinc-200 hover:bg-zinc-800 hover:text-white transition-colors"
          >
            {config.github.is_configured ? "Configure GitHub Settings" : "Connect GitHub Repository"}
          </button>
        </CardContent>
      </Card>

      {/* Jira Modal */}
      {showJiraModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-zinc-950 border border-zinc-800 rounded-xl p-6 space-y-4 shadow-2xl">
            <div className="flex justify-between items-center border-b border-zinc-800 pb-3">
              <h3 className="text-base font-bold text-white">Jira Cloud Settings</h3>
              <button onClick={() => setShowJiraModal(false)} className="text-zinc-400 hover:text-white">✕</button>
            </div>
            <form onSubmit={handleSaveJira} className="space-y-3 text-xs">
              <div>
                <label className="block text-zinc-400 mb-1">Host URL</label>
                <input
                  type="text"
                  required
                  placeholder="acme.atlassian.net"
                  value={jiraForm.host_url}
                  onChange={(e) => setJiraForm({ ...jiraForm, host_url: e.target.value })}
                  className="w-full rounded-md border border-zinc-800 bg-zinc-900 p-2 text-zinc-200"
                />
              </div>
              <div>
                <label className="block text-zinc-400 mb-1">Service Email</label>
                <input
                  type="email"
                  required
                  placeholder="sec-service@acme.com"
                  value={jiraForm.email}
                  onChange={(e) => setJiraForm({ ...jiraForm, email: e.target.value })}
                  className="w-full rounded-md border border-zinc-800 bg-zinc-900 p-2 text-zinc-200"
                />
              </div>
              <div>
                <label className="block text-zinc-400 mb-1">API Token (AES-256 Encrypted)</label>
                <input
                  type="password"
                  required
                  placeholder="Atlassian API Token"
                  value={jiraForm.api_token}
                  onChange={(e) => setJiraForm({ ...jiraForm, api_token: e.target.value })}
                  className="w-full rounded-md border border-zinc-800 bg-zinc-900 p-2 text-zinc-200"
                />
              </div>
              <div>
                <label className="block text-zinc-400 mb-1">Project Key</label>
                <input
                  type="text"
                  required
                  placeholder="SEC"
                  value={jiraForm.project_key}
                  onChange={(e) => setJiraForm({ ...jiraForm, project_key: e.target.value })}
                  className="w-full rounded-md border border-zinc-800 bg-zinc-900 p-2 text-zinc-200"
                />
              </div>
              {error && <p className="text-red-400 text-[11px]">{error}</p>}
              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowJiraModal(false)}
                  className="px-3 py-1.5 rounded-md bg-zinc-800 text-zinc-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-3 py-1.5 rounded-md bg-blue-600 text-white font-semibold"
                >
                  {saving ? "Encrypting & Saving..." : "Save Credentials"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* GitHub Modal */}
      {showGitHubModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-zinc-950 border border-zinc-800 rounded-xl p-6 space-y-4 shadow-2xl">
            <div className="flex justify-between items-center border-b border-zinc-800 pb-3">
              <h3 className="text-base font-bold text-white">GitHub Settings</h3>
              <button onClick={() => setShowGitHubModal(false)} className="text-zinc-400 hover:text-white">✕</button>
            </div>
            <form onSubmit={handleSaveGitHub} className="space-y-3 text-xs">
              <div>
                <label className="block text-zinc-400 mb-1">Repo Owner / Org</label>
                <input
                  type="text"
                  required
                  placeholder="acme-corp"
                  value={githubForm.repo_owner}
                  onChange={(e) => setGithubForm({ ...githubForm, repo_owner: e.target.value })}
                  className="w-full rounded-md border border-zinc-800 bg-zinc-900 p-2 text-zinc-200"
                />
              </div>
              <div>
                <label className="block text-zinc-400 mb-1">Repository Name</label>
                <input
                  type="text"
                  required
                  placeholder="payments-api"
                  value={githubForm.repo_name}
                  onChange={(e) => setGithubForm({ ...githubForm, repo_name: e.target.value })}
                  className="w-full rounded-md border border-zinc-800 bg-zinc-900 p-2 text-zinc-200"
                />
              </div>
              <div>
                <label className="block text-zinc-400 mb-1">Personal Access Token (AES-256 Encrypted)</label>
                <input
                  type="password"
                  required
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                  value={githubForm.personal_access_token}
                  onChange={(e) => setGithubForm({ ...githubForm, personal_access_token: e.target.value })}
                  className="w-full rounded-md border border-zinc-800 bg-zinc-900 p-2 text-zinc-200"
                />
              </div>
              {error && <p className="text-red-400 text-[11px]">{error}</p>}
              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowGitHubModal(false)}
                  className="px-3 py-1.5 rounded-md bg-zinc-800 text-zinc-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-3 py-1.5 rounded-md bg-purple-600 text-white font-semibold"
                >
                  {saving ? "Encrypting & Saving..." : "Save Credentials"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
