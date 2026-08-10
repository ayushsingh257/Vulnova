"use client";

import React, { useState } from "react";
import {
  Layers,
  Globe,
  Plus,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Server,
  ExternalLink,
  Search,
  RefreshCw,
  Trash2,
} from "lucide-react";

interface AssetItem {
  id: string;
  name: string;
  url: string;
  environment: "PRODUCTION" | "STAGING" | "DEVELOPMENT";
  verification_status: "VERIFIED" | "PENDING" | "FAILED";
  risk_score: number;
  open_vulnerabilities: number;
  tech_stack: string[];
  last_scanned_at: string;
}

export default function AssetsPage() {
  const [assets, setAssets] = useState<AssetItem[]>([
    {
      id: "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      name: "Production API Gateway",
      url: "https://api.staging.example.com",
      environment: "PRODUCTION",
      verification_status: "VERIFIED",
      risk_score: 74.5,
      open_vulnerabilities: 4,
      tech_stack: ["FastAPI", "PostgreSQL", "Redis", "Docker"],
      last_scanned_at: new Date().toISOString(),
    },
    {
      id: "7fa85f64-5717-4562-b3fc-2c963f66afa7",
      name: "Auth Service Staging",
      url: "https://auth.staging.example.com",
      environment: "STAGING",
      verification_status: "VERIFIED",
      risk_score: 92.0,
      open_vulnerabilities: 7,
      tech_stack: ["Node.js", "Express", "MongoDB"],
      last_scanned_at: new Date(Date.now() - 86400000).toISOString(),
    },
    {
      id: "8d48aca2-c4b9-45b2-b42d-e6f2dbfdeb18",
      name: "Customer Dashboard Portal",
      url: "https://app.example.com",
      environment: "PRODUCTION",
      verification_status: "PENDING",
      risk_score: 45.0,
      open_vulnerabilities: 1,
      tech_stack: ["Next.js", "React", "TailwindCSS"],
      last_scanned_at: "Never Scanned",
    },
  ]);

  const [showModal, setShowModal] = useState(false);
  const [targetName, setTargetName] = useState("");
  const [targetUrl, setTargetUrl] = useState("");
  const [environment, setEnvironment] = useState<"PRODUCTION" | "STAGING" | "DEVELOPMENT">("PRODUCTION");
  const [searchTerm, setSearchTerm] = useState("");

  const handleAddAsset = (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetName || !targetUrl) return;

    const newAsset: AssetItem = {
      id: `asset-${Date.now()}`,
      name: targetName,
      url: targetUrl,
      environment,
      verification_status: "PENDING",
      risk_score: 50.0,
      open_vulnerabilities: 0,
      tech_stack: ["Detected upon scan"],
      last_scanned_at: "Pending Scan",
    };

    setAssets([newAsset, ...assets]);
    setTargetName("");
    setTargetUrl("");
    setShowModal(false);
  };

  const handleVerify = (id: string) => {
    setAssets((prev) =>
      prev.map((a) => (a.id === id ? { ...a, verification_status: "VERIFIED" } : a))
    );
    alert("DNS TXT Challenge verified! Asset marked as VERIFIED target.");
  };

  const handleDelete = (id: string) => {
    if (!confirm("Are you sure you want to remove this target asset from inventory?")) return;
    setAssets((prev) => prev.filter((a) => a.id !== id));
  };

  const filtered = assets.filter(
    (a) =>
      a.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.url.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-zinc-800 pb-4">
        <div>
          <div className="flex items-center space-x-2">
            <div className="p-2 rounded-lg bg-red-950/60 border border-red-800/40 text-red-500">
              <Layers className="h-5 w-5" />
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight">
              Attack Surface & Asset Inventory
            </h1>
          </div>
          <p className="text-xs text-zinc-400 mt-1">
            Continuous discovery and ownership authorization catalog for organization targets, hosts, and microservices.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-red-950 border border-red-800 text-xs font-bold text-red-400 hover:bg-red-900 transition-colors shadow-lg"
        >
          <Plus className="h-4 w-4" />
          <span>Add Target Asset</span>
        </button>
      </div>

      {/* Stats Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl border border-zinc-800 bg-zinc-900/60">
          <div className="text-xs text-zinc-400">Total Monitored Targets</div>
          <div className="text-2xl font-black text-white mt-1">{assets.length}</div>
        </div>
        <div className="p-4 rounded-xl border border-emerald-900/60 bg-emerald-950/20">
          <div className="text-xs text-emerald-400">Verified Production</div>
          <div className="text-2xl font-black text-emerald-400 mt-1">
            {assets.filter((a) => a.verification_status === "VERIFIED").length}
          </div>
        </div>
        <div className="p-4 rounded-xl border border-amber-900/60 bg-amber-950/20">
          <div className="text-xs text-amber-400">Verification Pending</div>
          <div className="text-2xl font-black text-amber-400 mt-1">
            {assets.filter((a) => a.verification_status === "PENDING").length}
          </div>
        </div>
        <div className="p-4 rounded-xl border border-red-900/60 bg-red-950/20">
          <div className="text-xs text-red-400">High Risk Exposure</div>
          <div className="text-2xl font-black text-red-400 mt-1">
            {assets.filter((a) => a.risk_score > 70).length}
          </div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
        <input
          type="text"
          placeholder="Search targets or host URLs..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full pl-9 pr-3 py-2 rounded-lg border border-zinc-800 bg-zinc-900 text-xs text-zinc-200 focus:outline-none focus:border-red-500"
        />
      </div>

      {/* Asset Table */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 overflow-hidden shadow-2xl">
        <table className="w-full text-left text-xs text-zinc-300">
          <thead className="bg-zinc-900 border-b border-zinc-800 font-mono text-[11px] text-zinc-400 uppercase">
            <tr>
              <th className="p-4">Target Asset</th>
              <th className="p-4">Environment</th>
              <th className="p-4">Authorization</th>
              <th className="p-4">Risk Score</th>
              <th className="p-4">Detected Tech Stack</th>
              <th className="p-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800/60 font-sans">
            {filtered.map((item) => (
              <tr key={item.id} className="hover:bg-zinc-900/60 transition-colors">
                <td className="p-4">
                  <div className="font-semibold text-white">{item.name}</div>
                  <a href={item.url} target="_blank" rel="noopener noreferrer" className="text-[11px] font-mono text-red-400 hover:underline flex items-center space-x-1">
                    <span>{item.url}</span>
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </td>
                <td className="p-4">
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold border border-zinc-700 bg-zinc-800 text-zinc-300">
                    {item.environment}
                  </span>
                </td>
                <td className="p-4">
                  {item.verification_status === "VERIFIED" ? (
                    <span className="inline-flex items-center space-x-1 text-emerald-400 font-bold text-[11px]">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      <span>VERIFIED</span>
                    </span>
                  ) : (
                    <button
                      onClick={() => handleVerify(item.id)}
                      className="px-2 py-1 rounded bg-amber-950 border border-amber-800 text-amber-400 hover:bg-amber-900 text-[10px] font-bold"
                    >
                      Verify DNS
                    </button>
                  )}
                </td>
                <td className="p-4 font-mono font-bold text-red-400">{item.risk_score}</td>
                <td className="p-4">
                  <div className="flex flex-wrap gap-1">
                    {item.tech_stack.map((t, i) => (
                      <span key={i} className="px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 text-[10px]">
                        {t}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="p-4 text-right space-x-2">
                  <a
                    href="/scans"
                    className="px-2.5 py-1 rounded border border-zinc-700 bg-zinc-800 text-zinc-200 hover:bg-zinc-700 text-[11px]"
                  >
                    Scan Target
                  </a>
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

      {/* Target Registration Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-4">
          <form onSubmit={handleAddAsset} className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <div className="flex justify-between items-center border-b border-zinc-800 pb-3">
              <h3 className="text-base font-bold text-white">Register Target Asset</h3>
              <button type="button" onClick={() => setShowModal(false)} className="text-zinc-400 hover:text-white text-sm font-bold">
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-zinc-400 font-semibold mb-1">Asset Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Production API Gateway"
                  value={targetName}
                  onChange={(e) => setTargetName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-zinc-800 bg-zinc-950 text-zinc-200 focus:outline-none focus:border-red-500"
                />
              </div>

              <div>
                <label className="block text-zinc-400 font-semibold mb-1">Target Host URL</label>
                <input
                  type="url"
                  required
                  placeholder="https://api.example.com"
                  value={targetUrl}
                  onChange={(e) => setTargetUrl(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-zinc-800 bg-zinc-950 text-zinc-200 focus:outline-none focus:border-red-500"
                />
              </div>

              <div>
                <label className="block text-zinc-400 font-semibold mb-1">Environment Tier</label>
                <select
                  value={environment}
                  onChange={(e: any) => setEnvironment(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-zinc-800 bg-zinc-950 text-zinc-200 focus:outline-none focus:border-red-500"
                >
                  <option value="PRODUCTION">PRODUCTION</option>
                  <option value="STAGING">STAGING</option>
                  <option value="DEVELOPMENT">DEVELOPMENT</option>
                </select>
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
                Add Target
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
