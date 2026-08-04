"use client";

import React, { useEffect, useState } from "react";
import { AdminService, APIKeyAdminItem } from "@/services/admin.service";
import { APIKeyManagementPanel } from "@/components/settings/api-key-management-panel";

export default function SettingsAPIKeysPage() {
  const [apiKeys, setApiKeys] = useState<APIKeyAdminItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchKeys = async () => {
    try {
      setLoading(true);
      const data = await AdminService.listAPIKeys();
      setApiKeys(data.api_keys);
    } catch (err: any) {
      setError(err.message || "Failed to load integration API keys.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center text-sm text-zinc-400">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-red-500 border-t-transparent mr-3" />
        <span>Loading Integration API Keys...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 rounded-xl border border-red-500/20 bg-red-500/10 text-red-400 text-sm">
        {error}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="border-b border-zinc-800 pb-4">
        <h1 className="text-2xl font-bold text-zinc-100">
          Integration API Key Governance
        </h1>
        <p className="text-xs text-zinc-400 mt-1">
          Generate, inspect, and revoke machine-to-machine API keys for CI/CD pipelines and SDK integrations.
        </p>
      </div>

      <APIKeyManagementPanel
        apiKeys={apiKeys}
        onKeysUpdated={fetchKeys}
      />
    </div>
  );
}
