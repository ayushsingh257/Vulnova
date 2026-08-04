"use client";

import React, { useEffect, useState } from "react";
import { AdminService, SecurityOverviewAdmin } from "@/services/admin.service";
import { SecuritySettingsCard } from "@/components/settings/security-settings-card";

export default function SettingsSecurityPage() {
  const [security, setSecurity] = useState<SecurityOverviewAdmin | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadSecurity() {
      try {
        setLoading(true);
        const data = await AdminService.getSecurityOverview();
        setSecurity(data);
      } catch (err: any) {
        setError(err.message || "Failed to load security overview.");
      } finally {
        setLoading(false);
      }
    }

    loadSecurity();
  }, []);

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center text-sm text-zinc-400">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-red-500 border-t-transparent mr-3" />
        <span>Loading Security Overview...</span>
      </div>
    );
  }

  if (error || !security) {
    return (
      <div className="p-6 rounded-xl border border-red-500/20 bg-red-500/10 text-red-400 text-sm">
        {error || "Security posture data not found."}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="border-b border-zinc-800 pb-4">
        <h1 className="text-2xl font-bold text-zinc-100">
          Security Overview & MFA Status Visibility
        </h1>
        <p className="text-xs text-zinc-400 mt-1">
          Inspect authentication security policies, MFA enrollment status across team members, and audit logging settings.
        </p>
      </div>

      <SecuritySettingsCard security={security} />
    </div>
  );
}
