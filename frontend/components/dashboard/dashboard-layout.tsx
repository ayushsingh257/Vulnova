"use client";

import * as React from "react";
import {
  ShieldAlert,
  ShieldCheck,
  Link2,
  Bell,
  Activity,
  Calendar,
  Layers,
  FileText,
  Settings,
  User,
  Radio,
  Search,
  Server,
  PackageCheck,
  Boxes,
  KeyRound,
} from "lucide-react";

export interface DashboardLayoutProps {
  children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 font-sans antialiased selection:bg-red-500/30">
      {/* Top Header Bar */}
      <header className="sticky top-0 z-50 border-b border-zinc-800/80 bg-zinc-950/80 backdrop-blur-xl px-6 py-3.5 flex items-center justify-between shadow-2xl">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-red-600/20 border border-red-500/40 text-red-500 shadow-md shadow-red-950/50">
              <ShieldAlert className="h-5 w-5 animate-pulse" />
            </div>
            <div>
              <span className="text-lg font-extrabold tracking-wider text-white">VULNOVA</span>
              <span className="ml-2 rounded-full border border-red-500/30 bg-red-950/40 px-2 py-0.5 text-[10px] font-semibold text-red-400">
                SOC ENTERPRISE
              </span>
            </div>
          </div>

          <div className="hidden md:flex items-center space-x-2 border-l border-zinc-800 pl-4">
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
              <input
                type="text"
                placeholder="Search targets, findings, CVEs..."
                className="h-9 w-64 rounded-md border border-zinc-800 bg-zinc-900/60 pl-9 pr-4 text-xs text-zinc-200 placeholder-zinc-500 focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500"
              />
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="hidden sm:flex items-center space-x-2 rounded-full border border-emerald-900/50 bg-emerald-950/30 px-3 py-1 text-xs text-emerald-400">
            <Radio className="h-3.5 w-3.5 animate-ping text-emerald-500" />
            <span className="font-mono text-[11px]">WEBSOCKET STREAM ACTIVE</span>
          </div>

          <button className="relative p-2 text-zinc-400 hover:text-white transition-colors">
            <Bell className="h-5 w-5" />
            <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-red-500 ring-2 ring-zinc-950" />
          </button>

          <div className="flex items-center space-x-3 border-l border-zinc-800 pl-4">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-zinc-800 border border-zinc-700 text-zinc-300">
              <User className="h-4 w-4" />
            </div>
            <div className="hidden md:block text-left text-xs">
              <div className="font-semibold text-zinc-200">Security Analyst</div>
              <div className="text-[10px] text-zinc-400">Acme Corp Enterprise</div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Grid Layout with Sidebar */}
      <div className="flex">
        {/* Sidebar Navigation */}
        <aside className="hidden lg:flex w-64 flex-col border-r border-zinc-800/80 bg-zinc-950/40 p-4 space-y-6 min-h-[calc(100vh-57px)]">
          <div className="space-y-1">
            <div className="px-3 text-[10px] font-bold uppercase tracking-wider text-zinc-500 mb-2">
              Operations Control
            </div>
            <a
              href="/dashboard"
              className="flex items-center space-x-3 rounded-lg bg-red-950/40 border border-red-800/40 px-3 py-2.5 text-xs font-semibold text-red-400 transition-colors"
            >
              <Activity className="h-4 w-4" />
              <span>SOC Dashboard</span>
            </a>
            <a
              href="/scans"
              className="flex items-center space-x-3 rounded-lg px-3 py-2.5 text-xs font-medium text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200 transition-colors"
            >
              <Radio className="h-4 w-4" />
              <span>Active Scans</span>
            </a>
            <a
              href="/schedules"
              className="flex items-center space-x-3 rounded-lg px-3 py-2.5 text-xs font-medium text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200 transition-colors"
            >
              <Calendar className="h-4 w-4" />
              <span>Scan Schedules</span>
            </a>
            <a
              href="/integrations"
              className="flex items-center space-x-3 rounded-lg px-3 py-2.5 text-xs font-medium text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200 transition-colors"
            >
              <Link2 className="h-4 w-4" />
              <span>Integrations</span>
            </a>
            <a
              href="/notifications"
              className="flex items-center space-x-3 rounded-lg px-3 py-2.5 text-xs font-medium text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200 transition-colors"
            >
              <Bell className="h-4 w-4" />
              <span>Notifications</span>
            </a>
          </div>

          <div className="space-y-1">
            <div className="px-3 text-[10px] font-bold uppercase tracking-wider text-zinc-500 mb-2">
              Intelligence & Assets
            </div>
            <a
              href="/findings"
              className="flex items-center space-x-3 rounded-lg px-3 py-2.5 text-xs font-medium text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200 transition-colors"
            >
              <ShieldAlert className="h-4 w-4" />
              <span>Vulnerabilities</span>
            </a>
            <a
              href="/assets"
              className="flex items-center space-x-3 rounded-lg px-3 py-2.5 text-xs font-medium text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200 transition-colors"
            >
              <Layers className="h-4 w-4" />
              <span>Asset Inventory</span>
            </a>
            <a
              href="/reports"
              className="flex items-center space-x-3 rounded-lg px-3 py-2.5 text-xs font-medium text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200 transition-colors"
            >
              <FileText className="h-4 w-4" />
              <span>Executive Reports</span>
            </a>
            <a
              href="/compliance"
              className="flex items-center space-x-3 rounded-lg px-3 py-2.5 text-xs font-medium text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200 transition-colors"
            >
              <ShieldCheck className="h-4 w-4" />
              <span>Compliance Frameworks</span>
            </a>
            <a
              href="/validation/owasp"
              className="flex items-center space-x-3 rounded-lg px-3 py-2.5 text-xs font-medium text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200 transition-colors"
            >
              <ShieldCheck className="h-4 w-4 text-purple-400" />
              <span>OWASP Validation</span>
            </a>
            <a
              href="/validation/api-security"
              className="flex items-center space-x-3 rounded-lg px-3 py-2.5 text-xs font-medium text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200 transition-colors"
            >
              <Server className="h-4 w-4 text-blue-400" />
              <span>API Security Validation</span>
            </a>
            <a
              href="/validation/infrastructure"
              className="flex items-center space-x-3 rounded-lg px-3 py-2.5 text-xs font-medium text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200 transition-colors"
            >
              <ShieldCheck className="h-4 w-4 text-emerald-400" />
              <span>Infrastructure Validation</span>
            </a>
            <a
              href="/validation/pentest"
              className="flex items-center space-x-3 rounded-lg px-3 py-2.5 text-xs font-medium text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200 transition-colors"
            >
              <ShieldAlert className="h-4 w-4 text-red-400" />
              <span>Penetration Testing Validation</span>
            </a>
            <a
              href="/validation/sca"
              className="flex items-center space-x-3 rounded-lg px-3 py-2.5 text-xs font-medium text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200 transition-colors"
            >
              <PackageCheck className="h-4 w-4 text-blue-400" />
              <span>Dependency Security Validation</span>
            </a>
            <a
              href="/validation/container"
              className="flex items-center space-x-3 rounded-lg px-3 py-2.5 text-xs font-medium text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200 transition-colors"
            >
              <Boxes className="h-4 w-4 text-cyan-400" />
              <span>Container Security Validation</span>
            </a>
            <a
              href="/validation/secrets"
              className="flex items-center space-x-3 rounded-lg px-3 py-2.5 text-xs font-medium text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200 transition-colors"
            >
              <KeyRound className="h-4 w-4 text-purple-400" />
              <span>Secrets & Cryptography Validation</span>
            </a>
          </div>

          <div className="mt-auto pt-6 border-t border-zinc-800/80">
            <a
              href="/settings"
              className="flex items-center space-x-3 rounded-lg px-3 py-2.5 text-xs font-medium text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200 transition-colors"
            >
              <Settings className="h-4 w-4" />
              <span>Settings</span>
            </a>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 p-6 lg:p-8 overflow-y-auto max-w-7xl mx-auto space-y-8">
          {children}
        </main>
      </div>
    </div>
  );
}
