"use client";

import React, { useState } from "react";
import { DashboardLayout } from "@/components/dashboard/dashboard-layout";
import { PermissionGate } from "@/components/auth/permission-gate";
import {
  Calendar,
  Clock,
  Plus,
  Play,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Power,
  Trash2,
} from "lucide-react";

interface ScheduleItem {
  id: string;
  name: string;
  target_name: string;
  profile_name: string;
  cron_expression: string;
  next_run_at: string;
  status: "ACTIVE" | "PAUSED";
  last_run_status: "SUCCESS" | "FAILED";
}

export default function SchedulesPage() {
  const [schedules, setSchedules] = useState<ScheduleItem[]>([
    {
      id: "sched-001",
      name: "Daily Production API Recon",
      target_name: "Production API Gateway",
      profile_name: "FULL_RECON",
      cron_expression: "0 0 * * * (Daily at midnight)",
      next_run_at: new Date(Date.now() + 43200000).toISOString(),
      status: "ACTIVE",
      last_run_status: "SUCCESS",
    },
    {
      id: "sched-002",
      name: "Weekly Staging Security Audit",
      target_name: "Auth Service Staging",
      profile_name: "LIGHTWEIGHT_DAST",
      cron_expression: "0 2 * * 0 (Sundays at 02:00)",
      next_run_at: new Date(Date.now() + 259200000).toISOString(),
      status: "ACTIVE",
      last_run_status: "SUCCESS",
    },
    {
      id: "sched-003",
      name: "Monthly OWASP ASVS Compliance Scan",
      target_name: "Customer Dashboard UI",
      profile_name: "FULL_RECON",
      cron_expression: "0 0 1 * * (Monthly on the 1st)",
      next_run_at: new Date(Date.now() + 1296000000).toISOString(),
      status: "PAUSED",
      last_run_status: "SUCCESS",
    },
  ]);

  const [showModal, setShowModal] = useState(false);
  const [name, setName] = useState("");
  const [target, setTarget] = useState("Production API Gateway");
  const [profile, setProfile] = useState("FULL_RECON");
  const [cron, setCron] = useState("0 0 * * *");

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name) return;

    const newSchedule: ScheduleItem = {
      id: `sched-${Date.now()}`,
      name,
      target_name: target,
      profile_name: profile,
      cron_expression: cron,
      next_run_at: new Date(Date.now() + 86400000).toISOString(),
      status: "ACTIVE",
      last_run_status: "SUCCESS",
    };

    setSchedules([newSchedule, ...schedules]);
    setName("");
    setShowModal(false);
  };

  const toggleStatus = (id: string) => {
    setSchedules((prev) =>
      prev.map((s) =>
        s.id === id ? { ...s, status: s.status === "ACTIVE" ? "PAUSED" : "ACTIVE" } : s
      )
    );
  };

  const handleRunNow = (name: string) => {
    alert(`Immediate scan execution triggered for schedule "${name}". Scan job dispatched to Celery worker pool.`);
  };

  const handleDelete = (id: string) => {
    if (!confirm("Are you sure you want to delete this scan schedule?")) return;
    setSchedules((prev) => prev.filter((s) => s.id !== id));
  };

  return (
    <DashboardLayout>
      <PermissionGate>
        <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-zinc-800 pb-4">
        <div>
          <div className="flex items-center space-x-2">
            <div className="p-2 rounded-lg bg-red-950/60 border border-red-800/40 text-red-500">
              <Calendar className="h-5 w-5" />
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight">
              Automated Recurring Scan Schedules
            </h1>
          </div>
          <p className="text-xs text-zinc-400 mt-1">
            Configure automated continuous security validation routines, cron schedules, and recurring execution timers.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-red-950 border border-red-800 text-xs font-bold text-red-400 hover:bg-red-900 transition-colors shadow-lg"
        >
          <Plus className="h-4 w-4" />
          <span>Create Scan Schedule</span>
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-4 rounded-xl border border-zinc-800 bg-zinc-900/60">
          <div className="text-xs text-zinc-400">Total Configured Schedules</div>
          <div className="text-2xl font-black text-white mt-1">{schedules.length}</div>
        </div>
        <div className="p-4 rounded-xl border border-emerald-900/60 bg-emerald-950/20">
          <div className="text-xs text-emerald-400">Active Schedules</div>
          <div className="text-2xl font-black text-emerald-400 mt-1">
            {schedules.filter((s) => s.status === "ACTIVE").length}
          </div>
        </div>
        <div className="p-4 rounded-xl border border-blue-900/60 bg-blue-950/20">
          <div className="text-xs text-blue-400">Execution Success Rate</div>
          <div className="text-2xl font-black text-blue-400 mt-1">100%</div>
        </div>
      </div>

      {/* Schedule Table */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 overflow-hidden shadow-2xl">
        <table className="w-full text-left text-xs text-zinc-300">
          <thead className="bg-zinc-900 border-b border-zinc-800 font-mono text-[11px] text-zinc-400 uppercase">
            <tr>
              <th className="p-4">Schedule Name</th>
              <th className="p-4">Target Asset</th>
              <th className="p-4">Scan Profile</th>
              <th className="p-4">Recurrence Cron</th>
              <th className="p-4">Status</th>
              <th className="p-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/60 font-sans">
            {schedules.map((item) => (
              <tr key={item.id} className="hover:bg-zinc-900/60 transition-colors">
                <td className="p-4 font-semibold text-white">{item.name}</td>
                <td className="p-4 font-mono text-zinc-300">{item.target_name}</td>
                <td className="p-4 font-mono text-red-400">{item.profile_name}</td>
                <td className="p-4 font-mono text-zinc-400">{item.cron_expression}</td>
                <td className="p-4">
                  <button
                    onClick={() => toggleStatus(item.id)}
                    className={`px-2.5 py-1 rounded text-[10px] font-bold border transition-colors ${
                      item.status === "ACTIVE"
                        ? "bg-emerald-950 border-emerald-800 text-emerald-400"
                        : "bg-zinc-800 border-zinc-700 text-zinc-400"
                    }`}
                  >
                    {item.status}
                  </button>
                </td>
                <td className="p-4 text-right space-x-2">
                  <button
                    onClick={() => handleRunNow(item.name)}
                    className="px-2.5 py-1 rounded border border-red-800 bg-red-950 text-red-400 hover:bg-red-900 text-[11px] font-bold"
                  >
                    Run Now
                  </button>
                  <button
                    onClick={() => handleDelete(item.id)}
                    className="px-2 py-1 rounded border border-zinc-800 bg-zinc-900 text-zinc-500 hover:text-red-400"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Schedule Creation Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <form onSubmit={handleCreate} className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex justify-between items-center border-b border-zinc-800 pb-3">
              <h3 className="text-base font-bold text-white">Create Scan Schedule</h3>
              <button type="button" onClick={() => setShowModal(false)} className="text-zinc-400 hover:text-white text-sm font-bold">
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-zinc-400 font-semibold mb-1">Schedule Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Daily API Security Audit"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-zinc-800 bg-zinc-950 text-zinc-200 focus:outline-none focus:border-red-500"
                />
              </div>

              <div>
                <label className="block text-zinc-400 font-semibold mb-1">Target Scope</label>
                <select
                  value={target}
                  onChange={(e) => setTarget(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-zinc-800 bg-zinc-950 text-zinc-200 focus:outline-none focus:border-red-500"
                >
                  <option value="Production API Gateway">Production API Gateway</option>
                  <option value="Auth Service Staging">Auth Service Staging</option>
                  <option value="Customer Dashboard UI">Customer Dashboard UI</option>
                </select>
              </div>

              <div>
                <label className="block text-zinc-400 font-semibold mb-1">Scan Profile</label>
                <select
                  value={profile}
                  onChange={(e) => setProfile(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-zinc-800 bg-zinc-950 text-zinc-200 focus:outline-none focus:border-red-500"
                >
                  <option value="FULL_RECON">FULL_RECON (OWASP + Network)</option>
                  <option value="LIGHTWEIGHT_DAST">LIGHTWEIGHT_DAST</option>
                  <option value="API_SECURITY_AUDIT">API_SECURITY_AUDIT</option>
                </select>
              </div>

              <div>
                <label className="block text-zinc-400 font-semibold mb-1">Cron Recurrence Expression</label>
                <input
                  type="text"
                  required
                  placeholder="0 0 * * *"
                  value={cron}
                  onChange={(e) => setCron(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-zinc-800 bg-zinc-950 text-zinc-200 font-mono focus:outline-none focus:border-red-500"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-3 pt-4 border-t border-zinc-800">
              <button
                type="button"
                onClick={() => setShowModal(false)}
                className="px-4 py-2 rounded-lg border border-zinc-800 bg-zinc-950 text-xs font-semibold text-zinc-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 rounded-lg bg-red-950 border border-red-800 text-xs font-bold text-red-400 hover:bg-red-900"
              >
                Save Schedule
              </button>
            </div>
          </form>
        </div>
      )}
        </div>
      </PermissionGate>
    </DashboardLayout>
  );
}
