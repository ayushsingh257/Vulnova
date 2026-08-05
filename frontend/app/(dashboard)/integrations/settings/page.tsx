"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, ArrowLeft, Settings, ShieldCheck } from "lucide-react";
import { DashboardLayout } from "@/components/dashboard/dashboard-layout";
import {
  IntegrationConfigResponse,
  IntegrationsService,
} from "@/services/integrations.service";
import { IntegrationSettingsCard } from "@/components/integrations/IntegrationSettingsCard";

export default function IntegrationSettingsPage() {
  const router = useRouter();
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
      console.error("Failed to fetch integration settings:", err);
      setError(err.message || "Failed to load integration settings");
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
        <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
          <button
            onClick={() => router.push("/integrations")}
            className="flex items-center space-x-2 text-xs font-semibold text-zinc-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Back to Integration Control Plane</span>
          </button>
        </div>

        {loading ? (
          <div className="p-12 text-center text-zinc-400">
            <Loader2 className="w-8 h-8 animate-spin text-purple-400 mx-auto mb-3" />
            <p className="text-sm font-semibold text-zinc-300">
              Loading integration configuration...
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
