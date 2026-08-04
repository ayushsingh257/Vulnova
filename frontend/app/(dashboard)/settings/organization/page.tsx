"use client";

import React, { useEffect, useState } from "react";
import { AdminService, OrganizationAdmin } from "@/services/admin.service";

export default function SettingsOrganizationPage() {
  const [org, setOrg] = useState<OrganizationAdmin | null>(null);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const data = await AdminService.getOrganizationProfile();
        setOrg(data);
        setName(data.name);
      } catch (err: any) {
        setError(err.message || "Failed to load organization profile.");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsUpdating(true);
    setMessage(null);
    setError(null);
    try {
      const updated = await AdminService.updateOrganizationProfile(name);
      setOrg(updated);
      setMessage("Organization profile updated successfully!");
    } catch (err: any) {
      setError(err.message || "Failed to update profile.");
    } finally {
      setIsUpdating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center text-sm text-zinc-400">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-red-500 border-t-transparent mr-3" />
        <span>Loading Organization Profile...</span>
      </div>
    );
  }

  if (error || !org) {
    return (
      <div className="p-6 rounded-xl border border-red-500/20 bg-red-500/10 text-red-400 text-sm">
        {error || "Organization profile not found."}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="border-b border-zinc-800 pb-4">
        <h1 className="text-2xl font-bold text-zinc-100">
          Organization Profile & Settings
        </h1>
        <p className="text-xs text-zinc-400 mt-1">
          Manage workspace name, subscription plan metadata, and organization identifiers.
        </p>
      </div>

      {message && (
        <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/10 p-3 text-xs text-emerald-400">
          {message}
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
        {/* Profile Card */}
        <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-6 md:col-span-2">
          <form onSubmit={handleUpdate} className="flex flex-col gap-4">
            <div>
              <label className="text-xs font-semibold text-zinc-400 uppercase">
                Organization Display Name
              </label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-1 w-full rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-2 text-xs text-zinc-100 focus:border-red-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-zinc-400 uppercase">
                Organization URL Slug
              </label>
              <input
                type="text"
                disabled
                value={org.slug}
                className="mt-1 w-full rounded-lg border border-zinc-800/60 bg-zinc-900/40 px-3 py-2 text-xs text-zinc-500 font-mono"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-zinc-400 uppercase">
                Organization Identifier (UUID)
              </label>
              <input
                type="text"
                disabled
                value={org.id}
                className="mt-1 w-full rounded-lg border border-zinc-800/60 bg-zinc-900/40 px-3 py-2 text-xs text-zinc-500 font-mono"
              />
            </div>

            <div className="mt-4 flex justify-end border-t border-zinc-800 pt-4">
              <button
                type="submit"
                disabled={isUpdating}
                className="rounded-lg bg-red-600 px-4 py-2 text-xs font-semibold text-white hover:bg-red-500 disabled:opacity-50"
              >
                {isUpdating ? "Saving..." : "Save Profile Changes"}
              </button>
            </div>
          </form>
        </div>

        {/* Subscription Metadata Sidebar Card */}
        <div className="flex flex-col gap-4">
          <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-6">
            <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-400">
              Subscription Plan Tier
            </h3>
            <div className="mt-3 flex items-center justify-between">
              <span className="text-2xl font-black text-purple-400">
                {org.plan_tier}
              </span>
              <span className="rounded bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
                Active
              </span>
            </div>

            <div className="mt-4 pt-3 border-t border-zinc-800/60 flex flex-col gap-2 text-xs text-zinc-400">
              <div className="flex justify-between">
                <span>Team Members:</span>
                <span className="font-semibold text-zinc-200">{org.member_count}</span>
              </div>
              <div className="flex justify-between">
                <span>Active API Keys:</span>
                <span className="font-semibold text-zinc-200">{org.active_api_keys_count}</span>
              </div>
              <div className="flex justify-between">
                <span>Created:</span>
                <span className="font-mono text-zinc-400">
                  {new Date(org.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
