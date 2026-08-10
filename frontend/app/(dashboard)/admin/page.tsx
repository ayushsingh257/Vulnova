"use client";

import React, { useState } from "react";
import {
  Building2,
  Users,
  ShieldCheck,
  Activity,
  Server,
  KeyRound,
  FileText,
  Plus,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Settings,
  Lock,
  Radio,
} from "lucide-react";
import { DashboardLayout } from "@/components/dashboard/dashboard-layout";
import { PermissionGate } from "@/components/auth/permission-gate";
import { Button } from "@/components/ui/button";

export default function PlatformAdminPage() {
  const [selectedTenant, setSelectedTenant] = useState("CrowdStrike Enterprise");
  const [activeTab, setActiveTab] = useState<"tenants" | "roles" | "audit" | "system">("tenants");

  const tenants = [
    { name: "CrowdStrike Enterprise", plan: "ENTERPRISE SOC", users: 142, assets: 48, status: "ACTIVE", risk: "LOW" },
    { name: "Acme Corp Security", plan: "ENTERPRISE PRO", users: 56, assets: 24, status: "ACTIVE", risk: "ELEVATED" },
    { name: "CyberShield Systems", plan: "ENTERPRISE SOC", users: 89, assets: 36, status: "ACTIVE", risk: "LOW" },
    { name: "DefenseNet Global", plan: "TRIAL SOC", users: 12, assets: 8, status: "TRIAL", risk: "CRITICAL" },
  ];

  const auditEvents = [
    { time: "2 mins ago", event: "ORGANIZATION_CREATED", actor: "owner@vulnova.com", details: "Created CrowdStrike Enterprise workspace" },
    { time: "14 mins ago", event: "ROLE_PROMOTED", actor: "admin@crowdstrike.com", details: "Promoted user analyst-4@crowdstrike.com to SECURITY_ANALYST" },
    { time: "1 hour ago", event: "KMS_SECRET_ROTATED", actor: "SYSTEM_AUTOMATION", details: "Envelope key rotated for AWS KMS Alias vulnova-prod" },
    { time: "3 hours ago", event: "EVIDENCE_MALWARE_QUARANTINED", actor: "ClamAV_Daemon", details: "Flagged PE executable attachment in upload pipeline" },
  ];

  return (
    <DashboardLayout>
      <PermissionGate>
        <div className="space-y-8">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-zinc-800 pb-6">
            <div className="flex items-center space-x-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-red-600/20 border border-red-500/40 text-red-500 shadow-md">
                <Building2 className="h-6 w-6 animate-pulse" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h1 className="text-2xl font-extrabold tracking-tight text-white">
                    Platform Control Plane & Multi-Tenant Governance
                  </h1>
                  <span className="px-2 py-0.5 rounded bg-red-950 text-red-400 border border-red-800/40 text-[10px] font-bold font-mono">
                    OWNER ONLY
                  </span>
                </div>
                <p className="text-xs text-zinc-400 mt-0.5">
                  Global tenant isolation control, organization subscriptions, RBAC role matrices, and platform health telemetry.
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <Button variant="primary" size="sm" className="shadow-lg shadow-red-950/60">
                <Plus className="mr-1.5 h-4 w-4" />
                <span>Create New Organization</span>
              </Button>
            </div>
          </div>

          {/* Top Platform Metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-900/60 space-y-2">
              <div className="flex items-center justify-between text-xs text-zinc-400">
                <span>Active Subscribed Tenants</span>
                <Building2 className="h-4 w-4 text-red-400" />
              </div>
              <div className="text-2xl font-extrabold text-white font-mono">12 Tenants</div>
              <div className="text-[11px] text-emerald-400 font-mono flex items-center">
                <CheckCircle2 className="h-3 w-3 mr-1" />
                <span>100% Tenant Isolation Enforced</span>
              </div>
            </div>

            <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-900/60 space-y-2">
              <div className="flex items-center justify-between text-xs text-zinc-400">
                <span>Total Provisioned Users</span>
                <Users className="h-4 w-4 text-zinc-400" />
              </div>
              <div className="text-2xl font-extrabold text-white font-mono">299 Users</div>
              <div className="text-[11px] text-zinc-400">across 4 Hierarchical Roles</div>
            </div>

            <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-900/60 space-y-2">
              <div className="flex items-center justify-between text-xs text-zinc-400">
                <span>Isolated Scanner Workers</span>
                <Server className="h-4 w-4 text-cyan-400" />
              </div>
              <div className="text-2xl font-extrabold text-cyan-400 font-mono">48 Worker Pods</div>
              <div className="text-[11px] text-zinc-400 font-mono">UID 10001 • CAP_DROP_ALL</div>
            </div>

            <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-900/60 space-y-2">
              <div className="flex items-center justify-between text-xs text-zinc-400">
                <span>Global System Health</span>
                <Activity className="h-4 w-4 text-emerald-400" />
              </div>
              <div className="text-2xl font-extrabold text-emerald-400 font-mono">98.4 / 100</div>
              <div className="text-[11px] text-emerald-400 font-mono flex items-center">
                <Radio className="h-3 w-3 mr-1 animate-pulse" />
                <span>All Subsystems Operational</span>
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex items-center space-x-2 border-b border-zinc-800 pb-3 text-xs font-semibold">
            <button
              onClick={() => setActiveTab("tenants")}
              className={`px-4 py-2 rounded-lg transition-colors ${
                activeTab === "tenants" ? "bg-red-950/80 border border-red-800/60 text-red-400" : "text-zinc-400 hover:text-white"
              }`}
            >
              Multi-Tenant Organizations ({tenants.length})
            </button>
            <button
              onClick={() => setActiveTab("roles")}
              className={`px-4 py-2 rounded-lg transition-colors ${
                activeTab === "roles" ? "bg-red-950/80 border border-red-800/60 text-red-400" : "text-zinc-400 hover:text-white"
              }`}
            >
              Hierarchical RBAC Matrix
            </button>
            <button
              onClick={() => setActiveTab("audit")}
              className={`px-4 py-2 rounded-lg transition-colors ${
                activeTab === "audit" ? "bg-red-950/80 border border-red-800/60 text-red-400" : "text-zinc-400 hover:text-white"
              }`}
            >
              Platform Audit Stream
            </button>
            <button
              onClick={() => setActiveTab("system")}
              className={`px-4 py-2 rounded-lg transition-colors ${
                activeTab === "system" ? "bg-red-950/80 border border-red-800/60 text-red-400" : "text-zinc-400 hover:text-white"
              }`}
            >
              System Controls & Policies
            </button>
          </div>

          {/* Tab Content */}
          {activeTab === "tenants" && (
            <div className="space-y-4">
              <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-zinc-900 border-b border-zinc-800 text-zinc-400 font-semibold uppercase tracking-wider">
                    <tr>
                      <th className="p-4">Organization Name</th>
                      <th className="p-4">Subscription Plan</th>
                      <th className="p-4">Users</th>
                      <th className="p-4">Active Assets</th>
                      <th className="p-4">Posture Risk</th>
                      <th className="p-4">Status</th>
                      <th className="p-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-800/60 text-zinc-300">
                    {tenants.map((t, i) => (
                      <tr key={i} className="hover:bg-zinc-900/60 transition-colors">
                        <td className="p-4 font-bold text-white flex items-center space-x-2">
                          <Building2 className="h-4 w-4 text-red-400" />
                          <span>{t.name}</span>
                        </td>
                        <td className="p-4 font-mono text-zinc-400">{t.plan}</td>
                        <td className="p-4 font-mono">{t.users} users</td>
                        <td className="p-4 font-mono">{t.assets} target assets</td>
                        <td className="p-4 font-mono">
                          <span className={`px-2 py-0.5 rounded font-bold text-[10px] ${
                            t.risk === "LOW" ? "bg-emerald-950 text-emerald-400 border border-emerald-800/40" :
                            t.risk === "ELEVATED" ? "bg-amber-950 text-amber-400 border border-amber-800/40" :
                            "bg-red-950 text-red-400 border border-red-800/40"
                          }`}>
                            {t.risk}
                          </span>
                        </td>
                        <td className="p-4 font-mono text-emerald-400">🟢 {t.status}</td>
                        <td className="p-4 text-right">
                          <button
                            onClick={() => setSelectedTenant(t.name)}
                            className="px-3 py-1 rounded bg-zinc-800 text-zinc-200 hover:bg-zinc-700 transition-colors font-medium text-[11px]"
                          >
                            Switch Workspace
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === "roles" && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="p-6 rounded-xl border border-red-500/50 bg-red-950/20 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-white">OWNER</h3>
                  <span className="text-xs font-mono text-red-400">1 User</span>
                </div>
                <p className="text-xs text-zinc-400 leading-relaxed">
                  Full control over entire platform, all customer workspaces, tenant provisioning, system configurations, and billing.
                </p>
                <div className="text-[11px] font-mono text-red-400 pt-2 border-t border-red-900/40">
                  Access: /admin + All Subsystems
                </div>
              </div>

              <div className="p-6 rounded-xl border border-zinc-800 bg-zinc-900/40 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-white">ADMIN</h3>
                  <span className="text-xs font-mono text-zinc-400">14 Users</span>
                </div>
                <p className="text-xs text-zinc-400 leading-relaxed">
                  Organization-level management. Can invite employees, assign roles, configure scans, integrations, and secrets vault.
                </p>
                <div className="text-[11px] font-mono text-zinc-400 pt-2 border-t border-zinc-800">
                  Access: Org Control + SOC Dashboard
                </div>
              </div>

              <div className="p-6 rounded-xl border border-zinc-800 bg-zinc-900/40 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-white">SECURITY_ANALYST</h3>
                  <span className="text-xs font-mono text-zinc-400">86 Users</span>
                </div>
                <p className="text-xs text-zinc-400 leading-relaxed">
                  Day-to-day SOC analyst experience. Execute scans, triage vulnerabilities, inspect assets, export reports, and use AI reasoning.
                </p>
                <div className="text-[11px] font-mono text-zinc-400 pt-2 border-t border-zinc-800">
                  Access: SOC Operations & Intelligence
                </div>
              </div>

              <div className="p-6 rounded-xl border border-zinc-800 bg-zinc-900/40 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-bold text-white">VIEWER</h3>
                  <span className="text-xs font-mono text-zinc-400">32 Users</span>
                </div>
                <p className="text-xs text-zinc-400 leading-relaxed">
                  Read-only auditor access. Can inspect dashboards, view findings, and export executive PDF reports. Cannot execute scans.
                </p>
                <div className="text-[11px] font-mono text-zinc-400 pt-2 border-t border-zinc-800">
                  Access: Read-Only Dashboard & Reports
                </div>
              </div>
            </div>
          )}

          {activeTab === "audit" && (
            <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-6 space-y-4">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                Real-Time Platform Security Audit Events
              </h3>
              <div className="space-y-3">
                {auditEvents.map((evt, i) => (
                  <div key={i} className="flex items-start justify-between p-3.5 rounded-lg border border-zinc-800 bg-zinc-950 text-xs">
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className="font-mono font-bold text-red-400">{evt.event}</span>
                        <span className="text-zinc-500">•</span>
                        <span className="text-zinc-300 font-mono">{evt.actor}</span>
                      </div>
                      <p className="text-zinc-400">{evt.details}</p>
                    </div>
                    <span className="text-zinc-500 font-mono text-[11px] shrink-0">{evt.time}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === "system" && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
              <div className="p-6 rounded-xl border border-zinc-800 bg-zinc-900/40 space-y-4">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center space-x-2">
                  <Lock className="h-4 w-4 text-red-400" />
                  <span>Security & Access Controls</span>
                </h3>
                <ul className="space-y-3 text-zinc-300">
                  <li className="flex justify-between items-center p-2.5 rounded bg-zinc-950 border border-zinc-800">
                    <span>Multi-Tenant Schema Isolation</span>
                    <span className="text-emerald-400 font-mono font-bold">ENFORCED</span>
                  </li>
                  <li className="flex justify-between items-center p-2.5 rounded bg-zinc-950 border border-zinc-800">
                    <span>AWS KMS Envelope Encryption</span>
                    <span className="text-emerald-400 font-mono font-bold">ACTIVE (AES-256-GCM)</span>
                  </li>
                  <li className="flex justify-between items-center p-2.5 rounded bg-zinc-950 border border-zinc-800">
                    <span>Mandatory TOTP MFA Enforcement</span>
                    <span className="text-emerald-400 font-mono font-bold">ENFORCED</span>
                  </li>
                  <li className="flex justify-between items-center p-2.5 rounded bg-zinc-950 border border-zinc-800">
                    <span>RFC1918 Scanner Network Blocklists</span>
                    <span className="text-emerald-400 font-mono font-bold">ACTIVE</span>
                  </li>
                </ul>
              </div>

              <div className="p-6 rounded-xl border border-zinc-800 bg-zinc-900/40 space-y-4">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center space-x-2">
                  <Server className="h-4 w-4 text-cyan-400" />
                  <span>Subsystem Health & Infrastructure</span>
                </h3>
                <ul className="space-y-3 text-zinc-300">
                  <li className="flex justify-between items-center p-2.5 rounded bg-zinc-950 border border-zinc-800">
                    <span>PostgreSQL 16 Connection Pool</span>
                    <span className="text-emerald-400 font-mono font-bold">HEALTHY (5/20 Active)</span>
                  </li>
                  <li className="flex justify-between items-center p-2.5 rounded bg-zinc-950 border border-zinc-800">
                    <span>Redis 7 Metrics Cache</span>
                    <span className="text-emerald-400 font-mono font-bold">HEALTHY (TTL 30s)</span>
                  </li>
                  <li className="flex justify-between items-center p-2.5 rounded bg-zinc-950 border border-zinc-800">
                    <span>MinIO Evidence Quarantine Bucket</span>
                    <span className="text-emerald-400 font-mono font-bold">HEALTHY (0 Stale)</span>
                  </li>
                  <li className="flex justify-between items-center p-2.5 rounded bg-zinc-950 border border-zinc-800">
                    <span>ClamAV TCP Malware Daemon</span>
                    <span className="text-emerald-400 font-mono font-bold">LISTENING (Port 3310)</span>
                  </li>
                </ul>
              </div>
            </div>
          )}

        </div>
      </PermissionGate>
    </DashboardLayout>
  );
}
