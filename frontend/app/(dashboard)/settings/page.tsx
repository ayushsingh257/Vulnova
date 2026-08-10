"use client";

import React from "react";
import Link from "next/link";
import {
  Settings,
  KeyRound,
  Users,
  Shield,
  Building2,
  Lock,
  Link2,
  CreditCard,
  ChevronRight,
  ShieldAlert,
} from "lucide-react";

export default function SettingsHubPage() {
  const settingCategories = [
    {
      title: "Enterprise Secrets Vault & KMS",
      description: "Manage zero-trust envelope encryption (AES-256-GCM), external Key Management Systems (KMS), automated 90-day rotation, and secret access governance.",
      href: "/settings/secrets",
      icon: KeyRound,
      color: "text-emerald-400 border-emerald-900/60 bg-emerald-950/20",
    },
    {
      title: "API Keys & Machine Access",
      description: "Issue, monitor, and revoke machine-to-machine API integration tokens for automated CI/CD security pipelines.",
      href: "/settings/api-keys",
      icon: KeyRound,
      color: "text-blue-400 border-blue-900/60 bg-blue-950/20",
    },
    {
      title: "User Management & Invites",
      description: "Manage security team members, invite analysts, assign roles, and revoke organization access.",
      href: "/settings/users",
      icon: Users,
      color: "text-purple-400 border-purple-900/60 bg-purple-950/20",
    },
    {
      title: "Role-Based Access Control (RBAC)",
      description: "Configure granular permission matrices across ADMIN, SECURITY_ANALYST, AUDITOR, and DEVOPS roles.",
      href: "/settings/roles",
      icon: Shield,
      color: "text-amber-400 border-amber-900/60 bg-amber-950/20",
    },
    {
      title: "Organization Profile & Domain",
      description: "Update company details, domain ownership verification records, and enterprise contact information.",
      href: "/settings/organization",
      icon: Building2,
      color: "text-cyan-400 border-cyan-900/60 bg-cyan-950/20",
    },
    {
      title: "Security Governance & Policies",
      description: "Enforce IP whitelist restrictions, session idle timeouts, and password complexity parameters.",
      href: "/settings/security",
      icon: Lock,
      color: "text-red-400 border-red-900/60 bg-red-950/20",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-zinc-800 pb-4">
        <div>
          <div className="flex items-center space-x-2">
            <div className="p-2 rounded-lg bg-red-950/60 border border-red-800/40 text-red-500">
              <Settings className="h-5 w-5" />
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight">
              Enterprise Settings & Control Hub
            </h1>
          </div>
          <p className="text-xs text-zinc-400 mt-1">
            Centralized configuration portal for organization governance, secrets encryption, access control, and platform security.
          </p>
        </div>
      </div>

      {/* Tenant Plan Banner */}
      <div className="p-6 rounded-2xl border border-zinc-800 bg-gradient-to-r from-zinc-900 via-zinc-950 to-zinc-900 flex flex-col md:flex-row items-center justify-between gap-6 shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <span className="px-2.5 py-0.5 rounded text-[10px] font-extrabold bg-red-950 text-red-400 border border-red-800">
              ENTERPRISE TIER
            </span>
            <span className="text-xs font-mono text-zinc-400">Acme Corp Enterprise</span>
          </div>
          <h2 className="text-lg font-bold text-white">Active Plan: SOC Continuous Security Orchestration</h2>
          <p className="text-xs text-zinc-400">Unlimited Target Domains • 24/7 Container Sandboxing • Multi-KMS Vault Active</p>
        </div>
        <Link
          href="/settings/organization"
          className="px-4 py-2 rounded-lg border border-zinc-700 bg-zinc-800 text-xs font-semibold text-zinc-200 hover:bg-zinc-700 transition-colors"
        >
          Manage Subscription
        </Link>
      </div>

      {/* Settings Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {settingCategories.map((cat) => {
          const Icon = cat.icon;
          return (
            <Link
              key={cat.href}
              href={cat.href}
              className={`p-6 rounded-2xl border ${cat.color} hover:scale-[1.02] transition-all flex flex-col justify-between group shadow-lg`}
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="p-2.5 rounded-xl bg-zinc-900 border border-zinc-800">
                    <Icon className="h-5 w-5" />
                  </div>
                  <ChevronRight className="h-4 w-4 text-zinc-500 group-hover:text-white transition-colors" />
                </div>
                <h3 className="text-base font-bold text-white group-hover:text-red-400 transition-colors">
                  {cat.title}
                </h3>
                <p className="text-xs text-zinc-400 leading-relaxed">
                  {cat.description}
                </p>
              </div>
              <div className="pt-4 mt-4 border-t border-zinc-800/60 flex items-center text-xs font-semibold text-zinc-300">
                <span>Configure Settings</span>
                <ChevronRight className="h-3.5 w-3.5 ml-1 text-zinc-500" />
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
