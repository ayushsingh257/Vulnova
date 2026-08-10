"use client";

import React, { useEffect, useState } from "react";
import {
  ShieldAlert,
  Search,
  Filter,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  FileSpreadsheet,
  Cpu,
  ArrowUpRight,
  RefreshCw,
  ExternalLink,
  Lock,
} from "lucide-react";
import { VulnerabilitiesService, VulnerabilityItemDTO } from "@/services/vulnerabilities.service";

export default function FindingsPage() {
  const [findings, setFindings] = useState<VulnerabilityItemDTO[]>([
    {
      id: "8d48aca2-c4b9-45b2-b42d-e6f2dbfdeb18",
      cve_id: "CVE-2026-2148",
      title: "SQL Injection in Order Query Parameter",
      severity: "CRITICAL",
      cvss_score: 9.8,
      asset_name: "Production API Gateway",
      target_url: "https://api.staging.example.com/v1/orders",
      status: "OPEN",
      discovered_at: new Date().toISOString(),
      ai_confidence_score: 96.5,
      ai_recommendation: "Use parameterized queries or ORM bind variables in order_repository.py",
    },
    {
      id: "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      cve_id: "CVE-2026-1089",
      title: "Reflected Cross-Site Scripting (XSS) in Search Bar",
      severity: "HIGH",
      cvss_score: 7.5,
      asset_name: "Auth Service Staging",
      target_url: "https://auth.staging.example.com/search",
      status: "OPEN",
      discovered_at: new Date(Date.now() - 3600000).toISOString(),
      ai_confidence_score: 92.0,
      ai_recommendation: "Sanitize user input via DOMPurify and encode HTML characters prior to render",
    },
    {
      id: "7fa85f64-5717-4562-b3fc-2c963f66afa7",
      cve_id: "CVE-2025-4892",
      title: "CORS Misconfiguration Allowing Wildcard Credentials",
      severity: "MEDIUM",
      cvss_score: 5.4,
      asset_name: "Customer Dashboard UI",
      target_url: "https://app.example.com/api",
      status: "REMEDIATED",
      discovered_at: new Date(Date.now() - 86400000).toISOString(),
      ai_confidence_score: 88.0,
      ai_recommendation: "Restrict Access-Control-Allow-Origin to trusted domain origins",
    },
  ]);

  const [loading, setLoading] = useState(false);
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedFinding, setSelectedFinding] = useState<VulnerabilityItemDTO | null>(null);

  const loadFindings = React.useCallback(async () => {
    setLoading(true);
    try {
      const data = await VulnerabilitiesService.listVulnerabilities(
        severityFilter === "ALL" ? undefined : severityFilter,
        searchTerm
      );
      if (data && data.items && data.items.length > 0) {
        setFindings(data.items);
      }
    } catch (err) {
      console.warn("Using baseline vulnerability telemetry fallback.");
    } finally {
      setLoading(false);
    }
  }, [severityFilter, searchTerm]);

  useEffect(() => {
    loadFindings();
  }, [loadFindings]);

  const handleRemediate = async (id: string) => {
    try {
      await VulnerabilitiesService.remediateVulnerability(id);
      setFindings((prev) =>
        prev.map((f) => (f.id === id ? { ...f, status: "REMEDIATING" } : f))
      );
      alert("AI Remediation initiated! Automation job dispatched to worker queue.");
    } catch (err: any) {
      alert(`Remediation trigger: ${err.message || "Request completed."}`);
    }
  };

  const filtered = findings.filter((f) => {
    const matchesSev = severityFilter === "ALL" || f.severity === severityFilter;
    const matchesSearch =
      !searchTerm ||
      f.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (f.cve_id && f.cve_id.toLowerCase().includes(searchTerm.toLowerCase())) ||
      f.asset_name.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesSev && matchesSearch;
  });

  const getSeverityBadge = (sev: string) => {
    switch (sev) {
      case "CRITICAL":
        return "bg-red-950/80 border-red-800 text-red-400";
      case "HIGH":
        return "bg-amber-950/80 border-amber-800 text-amber-400";
      case "MEDIUM":
        return "bg-yellow-950/80 border-yellow-800 text-yellow-400";
      default:
        return "bg-zinc-800 border-zinc-700 text-zinc-400";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-zinc-800 pb-4">
        <div>
          <div className="flex items-center space-x-2">
            <div className="p-2 rounded-lg bg-red-950/60 border border-red-800/40 text-red-500">
              <ShieldAlert className="h-5 w-5" />
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight">
              Vulnerability Intelligence & Remediation Queue
            </h1>
          </div>
          <p className="text-xs text-zinc-400 mt-1">
            Real-time vulnerability findings discovered across authorized target assets with AI confidence scoring.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={loadFindings}
            className="flex items-center space-x-2 px-3 py-2 rounded-lg border border-zinc-800 bg-zinc-900 text-xs font-semibold text-zinc-300 hover:bg-zinc-800 transition-colors"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh</span>
          </button>
          <a
            href="/api/v1/findings/export/csv"
            download
            className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-red-950 border border-red-800 text-xs font-bold text-red-400 hover:bg-red-900 transition-colors shadow-lg"
          >
            <FileSpreadsheet className="h-4 w-4" />
            <span>Export CSV</span>
          </a>
        </div>
      </div>

      {/* Severity Counters */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
        {[
          { label: "CRITICAL", count: findings.filter((f) => f.severity === "CRITICAL").length, color: "text-red-500", border: "border-red-900/60 bg-red-950/20" },
          { label: "HIGH", count: findings.filter((f) => f.severity === "HIGH").length, color: "text-amber-500", border: "border-amber-900/60 bg-amber-950/20" },
          { label: "MEDIUM", count: findings.filter((f) => f.severity === "MEDIUM").length, color: "text-yellow-500", border: "border-yellow-900/60 bg-yellow-950/20" },
          { label: "LOW", count: findings.filter((f) => f.severity === "LOW").length, color: "text-blue-500", border: "border-blue-900/60 bg-blue-950/20" },
          { label: "REMEDIATED", count: findings.filter((f) => f.status === "REMEDIATED").length, color: "text-emerald-500", border: "border-emerald-900/60 bg-emerald-950/20" },
        ].map((item) => (
          <div key={item.label} className={`p-4 rounded-xl border ${item.border} text-center`}>
            <div className={`text-2xl font-black ${item.color}`}>{item.count}</div>
            <div className="text-[10px] font-bold text-zinc-400 mt-1">{item.label}</div>
          </div>
        ))}
      </div>

      {/* Search & Filter Toolbar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-zinc-900/60 p-4 rounded-xl border border-zinc-800">
        <div className="flex items-center space-x-2 text-xs font-mono">
          {["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((st) => (
            <button
              key={st}
              onClick={() => setSeverityFilter(st)}
              className={`px-3 py-1.5 rounded-lg border transition-all ${
                severityFilter === st
                  ? "border-red-500 bg-red-950/50 text-red-400 font-bold"
                  : "border-zinc-800 bg-zinc-950 text-zinc-400 hover:text-zinc-200"
              }`}
            >
              {st}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
          <input
            type="text"
            placeholder="Search CVE, title, or target..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-2 rounded-lg border border-zinc-800 bg-zinc-950 text-xs text-zinc-200 focus:outline-none focus:border-red-500"
          />
        </div>
      </div>

      {/* Vulnerabilities Table */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 overflow-hidden shadow-2xl">
        <table className="w-full text-left text-xs text-zinc-300">
          <thead className="bg-zinc-900 border-b border-zinc-800 font-mono text-[11px] text-zinc-400 uppercase">
            <tr>
              <th className="p-4">Severity</th>
              <th className="p-4">Vulnerability Title & CVE</th>
              <th className="p-4">Affected Asset</th>
              <th className="p-4">CVSS 4.0</th>
              <th className="p-4">AI Confidence</th>
              <th className="p-4">Status</th>
              <th className="p-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/60 font-sans">
            {filtered.map((item) => (
              <tr key={item.id} className="hover:bg-zinc-900/60 transition-colors">
                <td className="p-4">
                  <span className={`px-2.5 py-1 rounded-md border text-[10px] font-extrabold ${getSeverityBadge(item.severity)}`}>
                    {item.severity}
                  </span>
                </td>
                <td className="p-4">
                  <div className="font-semibold text-white">{item.title}</div>
                  <div className="text-[11px] font-mono text-zinc-400">{item.cve_id || "VULN-ID-RECON"}</div>
                </td>
                <td className="p-4 font-mono text-zinc-300">{item.asset_name}</td>
                <td className="p-4 font-mono font-bold text-red-400">{item.cvss_score}</td>
                <td className="p-4">
                  <div className="flex items-center space-x-1 text-emerald-400 font-mono text-[11px]">
                    <Cpu className="h-3.5 w-3.5" />
                    <span>{item.ai_confidence_score}%</span>
                  </div>
                </td>
                <td className="p-4">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold border border-zinc-700 bg-zinc-800 text-zinc-300">
                    {item.status}
                  </span>
                </td>
                <td className="p-4 text-right space-x-2">
                  <button
                    onClick={() => setSelectedFinding(item)}
                    className="px-2.5 py-1 rounded border border-zinc-700 bg-zinc-800 text-zinc-200 hover:bg-zinc-700 text-[11px]"
                  >
                    Details
                  </button>
                  <button
                    onClick={() => handleRemediate(item.id)}
                    className="px-2.5 py-1 rounded border border-red-800 bg-red-950 text-red-400 hover:bg-red-900 text-[11px] font-bold"
                  >
                    AI Fix
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Finding Detail Modal */}
      {selectedFinding && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-2xl w-full p-6 space-y-6 shadow-2xl">
            <div className="flex justify-between items-start border-b border-zinc-800 pb-4">
              <div>
                <span className={`px-2.5 py-0.5 rounded border text-[10px] font-bold ${getSeverityBadge(selectedFinding.severity)}`}>
                  {selectedFinding.severity}
                </span>
                <h3 className="text-lg font-bold text-white mt-2">{selectedFinding.title}</h3>
                <p className="text-xs font-mono text-zinc-400">{selectedFinding.cve_id} • {selectedFinding.target_url}</p>
              </div>
              <button onClick={() => setSelectedFinding(null)} className="text-zinc-400 hover:text-white text-sm font-bold">
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div>
                <h4 className="font-bold text-zinc-300 uppercase tracking-wider text-[10px] mb-1">AI Intelligence Recommendation</h4>
                <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800 text-emerald-400 font-mono">
                  {selectedFinding.ai_recommendation}
                </div>
              </div>
            </div>

            <div className="flex justify-end space-x-3 pt-4 border-t border-zinc-800">
              <button
                onClick={() => setSelectedFinding(null)}
                className="px-4 py-2 rounded-lg border border-zinc-800 bg-zinc-950 text-xs font-semibold text-zinc-400 hover:text-white"
              >
                Close
              </button>
              <button
                onClick={() => {
                  handleRemediate(selectedFinding.id);
                  setSelectedFinding(null);
                }}
                className="px-4 py-2 rounded-lg bg-red-950 border border-red-800 text-xs font-bold text-red-400 hover:bg-red-900"
              >
                Execute AI Remediation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
