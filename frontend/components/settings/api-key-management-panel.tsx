"use client";

import React, { useState } from "react";
import {
  APIKeyAdminItem,
  CreateAPIKeyAdminResponse,
  AdminService,
} from "@/services/admin.service";

interface APIKeyManagementPanelProps {
  apiKeys: APIKeyAdminItem[];
  onKeysUpdated: () => void;
}

export const APIKeyManagementPanel: React.FC<APIKeyManagementPanelProps> = ({
  apiKeys,
  onKeysUpdated,
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [name, setName] = useState("");
  const [selectedScopes, setSelectedScopes] = useState<string[]>([
    "scans:read",
    "findings:read",
  ]);
  const [createdResponse, setCreatedResponse] =
    useState<CreateAPIKeyAdminResponse | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const availableScopes = [
    { key: "scans:read", label: "Read Scan Jobs & Telemetry" },
    { key: "scans:create", label: "Trigger Assessment Scans" },
    { key: "findings:read", label: "Read Vulnerability Findings" },
    { key: "assets:read", label: "Read Asset Inventory" },
    { key: "reports:read", label: "Read Executive Summaries" },
  ];

  const toggleScope = (scope: string) => {
    if (selectedScopes.includes(scope)) {
      setSelectedScopes(selectedScopes.filter((s) => s !== scope));
    } else {
      setSelectedScopes([...selectedScopes, scope]);
    }
  };

  const handleGenerateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsGenerating(true);
    setErrorMessage(null);
    try {
      const res = await AdminService.createAPIKey({
        name,
        scopes: selectedScopes,
      });
      setCreatedResponse(res);
      onKeysUpdated();
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to generate API key.");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleRevoke = async (keyId: string) => {
    if (!confirm("Are you sure you want to revoke this integration API key?")) return;
    try {
      await AdminService.revokeAPIKey(keyId);
      onKeysUpdated();
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to revoke API key.");
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold text-zinc-100">
            Machine-to-Machine Integration API Keys
          </h3>
          <p className="text-xs text-zinc-400">
            API keys allow CI/CD pipelines and external automation to authenticate securely.
          </p>
        </div>

        <button
          onClick={() => {
            setCreatedResponse(null);
            setName("");
            setIsModalOpen(true);
          }}
          className="rounded-lg bg-red-600 px-4 py-2 text-xs font-semibold text-white hover:bg-red-500"
        >
          + Generate New API Key
        </button>
      </div>

      {errorMessage && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-400">
          {errorMessage}
        </div>
      )}

      {/* API Key List Table */}
      <div className="overflow-x-auto rounded-xl border border-zinc-800 bg-zinc-950">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-zinc-800 bg-zinc-900/50 uppercase tracking-wider text-zinc-400 font-semibold">
            <tr>
              <th className="px-6 py-3">Key Name</th>
              <th className="px-6 py-3">Key Prefix</th>
              <th className="px-6 py-3">Permission Scopes</th>
              <th className="px-6 py-3">Created</th>
              <th className="px-6 py-3">Last Used</th>
              <th className="px-6 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/60 text-zinc-300">
            {apiKeys.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-8 text-center text-zinc-500">
                  No active integration API keys found. Click &quot;+ Generate New API Key&quot; to create one.

                </td>
              </tr>
            ) : (
              apiKeys.map((key) => (
                <tr key={key.id} className="hover:bg-zinc-900/40 transition-all">
                  <td className="px-6 py-4 font-bold text-zinc-100">
                    {key.name}
                  </td>
                  <td className="px-6 py-4 font-mono text-zinc-300">
                    {key.key_prefix}••••••••
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-1">
                      {key.scopes.map((s) => (
                        <span
                          key={s}
                          className="rounded bg-zinc-800 px-2 py-0.5 text-[10px] font-mono text-zinc-300"
                        >
                          {s}
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-6 py-4 font-mono text-zinc-400">
                    {new Date(key.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 font-mono text-zinc-400">
                    {key.last_used_at
                      ? new Date(key.last_used_at).toLocaleDateString()
                      : "Never"}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => handleRevoke(key.id)}
                      className="rounded border border-red-500/20 bg-red-500/10 px-2.5 py-1 text-[10px] font-semibold text-red-400 hover:bg-red-500/20"
                    >
                      Revoke Key
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Create Key Modal Dialog */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-lg rounded-xl border border-zinc-800 bg-zinc-950 p-6 shadow-2xl">
            {!createdResponse ? (
              <>
                <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
                  <h3 className="text-lg font-bold text-zinc-100">
                    Generate Integration API Key
                  </h3>
                  <button
                    onClick={() => setIsModalOpen(false)}
                    className="text-zinc-400 hover:text-zinc-100"
                  >
                    ✕
                  </button>
                </div>

                <form onSubmit={handleGenerateKey} className="mt-4 flex flex-col gap-4">
                  <div>
                    <label className="text-xs font-semibold text-zinc-400 uppercase">
                      Key Description Name
                    </label>
                    <input
                      type="text"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="e.g. GitHub Actions CI/CD Pipeline"
                      className="mt-1 w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs text-zinc-100 placeholder-zinc-500 focus:border-red-500 focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-zinc-400 uppercase">
                      Select Granted Scopes
                    </label>
                    <div className="mt-2 flex flex-col gap-2">
                      {availableScopes.map((scope) => (
                        <label
                          key={scope.key}
                          className="flex items-center gap-2 text-xs text-zinc-300 cursor-pointer"
                        >
                          <input
                            type="checkbox"
                            checked={selectedScopes.includes(scope.key)}
                            onChange={() => toggleScope(scope.key)}
                            className="rounded border-zinc-800 text-red-600 focus:ring-0"
                          />
                          <span className="font-mono">{scope.key}</span>
                          <span className="text-zinc-500 text-[10px]">
                            ({scope.label})
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>

                  <div className="mt-4 flex justify-end gap-3 border-t border-zinc-800 pt-4">
                    <button
                      type="button"
                      onClick={() => setIsModalOpen(false)}
                      className="rounded-lg border border-zinc-800 bg-zinc-900 px-4 py-2 text-xs font-semibold text-zinc-400 hover:text-zinc-100"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isGenerating}
                      className="rounded-lg bg-red-600 px-4 py-2 text-xs font-semibold text-white hover:bg-red-500 disabled:opacity-50"
                    >
                      {isGenerating ? "Generating..." : "Generate Secret Key"}
                    </button>
                  </div>
                </form>
              </>
            ) : (
              <>
                {/* Show Secret Key Once Dialog */}
                <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
                  <h3 className="text-lg font-bold text-emerald-400">
                    ✓ API Key Generated Successfully
                  </h3>
                </div>

                <div className="mt-4 flex flex-col gap-3">
                  <p className="text-xs text-zinc-300">
                    Please copy your new API key now. <span className="font-bold text-amber-400">You will not be able to see it again!</span>
                  </p>

                  <div className="rounded-lg border border-emerald-500/30 bg-zinc-900 p-4 font-mono text-xs text-emerald-400 break-all select-all">
                    {createdResponse.raw_api_key}
                  </div>
                </div>

                <div className="mt-6 flex justify-end border-t border-zinc-800 pt-4">
                  <button
                    onClick={() => setIsModalOpen(false)}
                    className="rounded-lg bg-zinc-800 px-4 py-2 text-xs font-semibold text-zinc-200 hover:bg-zinc-700"
                  >
                    I Have Saved My Secret Key
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
