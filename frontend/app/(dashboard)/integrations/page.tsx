"use client";

import React, { useEffect, useState } from "react";
import { Loader2, Server, Github, Link2, Settings } from "lucide-react";
import { DashboardLayout } from "@/components/dashboard/dashboard-layout";
import {
  IntegrationConfigResponse,
  IntegrationsService,
} from "@/services/integrations.service";
import { IntegrationSettingsCard } from "@/components/integrations/IntegrationSettingsCard";

export default function IntegrationsDashboardPage() {
  const [config, setConfig] = useState<IntegrationConfigResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await IntegrationsService.getIntegrationStatus();
      setConfig(data);
    } catch (err: any) {
      console.error("Failed to fetch integration status:", err);
      setError(err.message || "Failed to load integration status");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-zinc-800 pb-6">
          <div className="flex items-center space-x-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-600/20 border border-purple-500/40 text-purple-400 shadow-md">
              <Link2 className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-black tracking-tight text-white">
                Enterprise Integration Control Plane
              </h1>
              <p className="text-xs text-zinc-400 mt-0.5">
                Bi-directional vulnerability synchronization with Jira Cloud and GitHub Issues
              </p>
            </div>
          </div>

          <a
            href="/integrations/settings"
            className="flex items-center space-x-2 rounded-xl bg-zinc-900 border border-zinc-800 px-4 py-2 text-xs font-semibold text-zinc-200 hover:bg-zinc-800 hover:text-white transition-colors"
          >
            <Settings className="h-4 w-4" />
            <span>Integration Settings</span>
          </a>
        </div>

        {loading ? (
          <div className="p-12 text-center text-zinc-400">
            <Loader2 className="w-8 h-8 animate-spin text-purple-400 mx-auto mb-3" />
            <p className="text-sm font-semibold text-zinc-300">
              Loading enterprise integration status...
            </p>
          </div>
        ) : error ? (
          <div className="rounded-xl border border-red-900/60 bg-red-950/20 p-6 text-center text-red-400 text-xs font-semibold">
            {error}
          </div>
        ) : config ? (
          <div className="space-y-8">
            <IntegrationSettingsCard config={config} onRefresh={fetchStatus} />
          </div>
        ) : null}
      </div>
    </DashboardLayout>
  );
}
