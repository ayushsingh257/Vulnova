"use client";

import React, { useState, useCallback } from "react";
import {
  PluginSecurityService,
  PluginSecurityReport,
  PluginSignatureVerificationResult,
  PluginExecutionResult,
  TrustedPublisher,
} from "@/services/plugin_security.service";

interface PluginSecurityPanelProps {
  pluginId: string;
}

const trustStatusConfig: Record<
  string,
  { color: string; bg: string; border: string; label: string }
> = {
  TRUSTED: {
    color: "text-emerald-400",
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/30",
    label: "Trusted Publisher",
  },
  REVOKED: {
    color: "text-red-400",
    bg: "bg-red-500/10",
    border: "border-red-500/30",
    label: "Revoked Publisher",
  },
  PENDING: {
    color: "text-amber-400",
    bg: "bg-amber-500/10",
    border: "border-amber-500/30",
    label: "Pending Verification",
  },
  UNTRUSTED: {
    color: "text-zinc-400",
    bg: "bg-zinc-500/10",
    border: "border-zinc-500/30",
    label: "Untrusted / Unknown",
  },
};

const capabilityLabels: Record<string, { label: string; icon: string; sensitive: boolean }> = {
  "network:http": { label: "HTTP/HTTPS Network Access", icon: "🌐", sensitive: false },
  "network:dns": { label: "DNS Resolution Probes", icon: "🔍", sensitive: false },
  "network:tcp": { label: "Raw TCP Port Probes", icon: "🔌", sensitive: false },
  "filesystem:read": { label: "Read Sandbox Filesystem", icon: "📂", sensitive: false },
  "filesystem:write": { label: "Write Sandbox Output", icon: "💾", sensitive: true },
  "process:execute": { label: "Spawn Isolated Subprocess", icon: "⚙️", sensitive: true },
};

export const PluginSecurityPanel: React.FC<PluginSecurityPanelProps> = ({
  pluginId,
}) => {
  const [report, setReport] = useState<PluginSecurityReport | null>(null);
  const [verificationResult, setVerificationResult] = useState<PluginSignatureVerificationResult | null>(null);
  const [executionResult, setExecutionResult] = useState<PluginExecutionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const fetchSecurityReport = useCallback(async () => {
    setLoading(true);
    setActionMessage(null);
    try {
      const data = await PluginSecurityService.getSecurityReport(pluginId);
      setReport(data);
    } catch (err: unknown) {
      setActionMessage(`Error: ${err instanceof Error ? err.message : "Failed to load report"}`);
    } finally {
      setLoading(false);
    }
  }, [pluginId]);

  const handleExecuteSandbox = async () => {
    setLoading(true);
    setActionMessage(null);
    try {
      const res = await PluginSecurityService.executePlugin({
        plugin_id: pluginId,
        target_url: "https://example.com",
        timeout_seconds: 30,
      });
      setExecutionResult(res);
      setActionMessage(`Plugin executed successfully in sandbox (${res.duration_ms.toFixed(1)}ms).`);
      await fetchSecurityReport();
    } catch (err: unknown) {
      setActionMessage(`Execution Blocked: ${err instanceof Error ? err.message : "Failed"}`);
    } finally {
      setLoading(false);
    }
  };

  const trustInfo = report ? trustStatusConfig[report.trust_status] || trustStatusConfig.UNTRUSTED : trustStatusConfig.UNTRUSTED;

  return (
    <div className="bg-zinc-900/80 border border-zinc-800 rounded-xl p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
        <div className="flex items-center space-x-3">
          <div className="h-10 w-10 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 font-bold text-lg">
            🔐
          </div>
          <div>
            <h3 className="text-lg font-semibold text-zinc-100">
              Plugin Zero-Trust Security & Sandbox Isolation
            </h3>
            <p className="text-xs text-zinc-400">
              Ed25519 cryptographic signature verification and capability-gated execution
            </p>
          </div>
        </div>

        <button
          onClick={fetchSecurityReport}
          disabled={loading}
          className="px-3 py-1.5 text-xs font-medium bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-lg transition disabled:opacity-50"
        >
          {loading ? "Loading..." : "Refresh Security Report"}
        </button>
      </div>

      {actionMessage && (
        <div className="p-3 bg-zinc-800/80 border border-zinc-700 rounded-lg text-xs text-zinc-300">
          {actionMessage}
        </div>
      )}

      {report && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Card 1: Signature & Trust */}
          <div className="p-4 bg-zinc-950/60 border border-zinc-800 rounded-lg space-y-3">
            <span className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
              Cryptographic Signature
            </span>
            <div className="flex items-center justify-between">
              <span className={`text-sm font-semibold ${report.signature_valid ? "text-emerald-400" : "text-red-400"}`}>
                {report.signature_valid ? "✓ Valid Ed25519" : "✗ Unsigned / Invalid"}
              </span>
              <span className={`px-2 py-0.5 text-xs rounded-full border font-medium ${trustInfo.bg} ${trustInfo.color} ${trustInfo.border}`}>
                {trustInfo.label}
              </span>
            </div>
            <div className="text-xs text-zinc-400 space-y-1">
              <div>Publisher: <span className="text-zinc-200 font-medium">{report.publisher_name} ({report.publisher_id})</span></div>
              {report.last_verified_at && (
                <div>Verified: <span className="text-zinc-300">{new Date(report.last_verified_at).toLocaleString()}</span></div>
              )}
            </div>
          </div>

          {/* Card 2: Sandbox Isolation */}
          <div className="p-4 bg-zinc-950/60 border border-zinc-800 rounded-lg space-y-3">
            <span className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
              Sandbox Runtime Policy
            </span>
            <div className="flex items-center space-x-2">
              <span className="text-sm font-semibold text-emerald-400">
                🛡️ Out-of-Process Isolation
              </span>
            </div>
            <div className="text-xs text-zinc-400 space-y-1">
              <div>CPU Limit: <span className="text-zinc-200">1.0 Core</span></div>
              <div>Memory Limit: <span className="text-zinc-200">256 MB Max</span></div>
              <div>Execution Timeout: <span className="text-zinc-200">30s Guard</span></div>
            </div>
          </div>

          {/* Card 3: Execution Metrics */}
          <div className="p-4 bg-zinc-950/60 border border-zinc-800 rounded-lg space-y-3">
            <span className="text-xs font-medium text-zinc-400 uppercase tracking-wider">
              Audit Telemetry
            </span>
            <div className="flex items-center justify-between">
              <div>
                <div className="text-2xl font-bold text-zinc-100">{report.total_executions}</div>
                <div className="text-xs text-zinc-500">Total Runs</div>
              </div>
              <div>
                <div className={`text-2xl font-bold ${report.blocked_executions > 0 ? "text-red-400" : "text-zinc-400"}`}>
                  {report.blocked_executions}
                </div>
                <div className="text-xs text-zinc-500">Blocked Runs</div>
              </div>
            </div>
            <button
              onClick={handleExecuteSandbox}
              disabled={loading || !report.signature_valid}
              className="w-full mt-2 px-3 py-1.5 text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Test Sandboxed Execution
            </button>
          </div>
        </div>
      )}

      {/* Capability Manifest Breakdown */}
      {report && (
        <div className="space-y-3">
          <h4 className="text-sm font-semibold text-zinc-200 flex items-center space-x-2">
            <span>📋 Declared Runtime Capabilities ({report.capabilities.length})</span>
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {report.capabilities.map((cap) => {
              const info = capabilityLabels[cap] || { label: cap, icon: "⚡", sensitive: false };
              return (
                <div
                  key={cap}
                  className="flex items-center justify-between p-2.5 bg-zinc-950/40 border border-zinc-800 rounded-lg"
                >
                  <div className="flex items-center space-x-2">
                    <span className="text-base">{info.icon}</span>
                    <span className="text-xs font-medium text-zinc-200">{info.label}</span>
                  </div>
                  <span className={`px-2 py-0.5 text-[10px] font-mono rounded ${info.sensitive ? "bg-amber-500/10 text-amber-400 border border-amber-500/30" : "bg-zinc-800 text-zinc-400"}`}>
                    {cap}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Execution Result Log */}
      {executionResult && (
        <div className="p-4 bg-zinc-950 border border-zinc-800 rounded-lg space-y-2 font-mono text-xs">
          <div className="flex items-center justify-between text-zinc-400">
            <span>Status: <span className={executionResult.status === "SUCCESS" ? "text-emerald-400 font-bold" : "text-red-400 font-bold"}>{executionResult.status}</span></span>
            <span>Duration: {executionResult.duration_ms.toFixed(1)}ms</span>
            <span>Driver: {executionResult.sandbox_driver}</span>
          </div>
          {executionResult.error && (
            <div className="text-red-400 mt-1">{executionResult.error}</div>
          )}
        </div>
      )}
    </div>
  );
};
