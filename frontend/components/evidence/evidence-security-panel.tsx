"use client";

import React, { useEffect, useState } from "react";
import {
  EvidenceMalwareService,
  EvidenceUploadResponseDTO,
  QuarantineDashboardSummaryDTO,
} from "../../services/evidence_malware.service";

interface EvidenceSecurityPanelProps {
  token?: string;
  userRole?: string;
}

export function EvidenceSecurityPanel({
  token,
  userRole = "ADMIN",
}: EvidenceSecurityPanelProps) {
  const [summary, setSummary] = useState<QuarantineDashboardSummaryDTO | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // File Upload State
  const [uploading, setUploading] = useState<boolean>(false);
  const [uploadResult, setUploadResult] = useState<EvidenceUploadResponseDTO | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const getAuthToken = () => {
    if (token) return token;
    if (typeof window !== "undefined") {
      return localStorage.getItem("token") || undefined;
    }
    return undefined;
  };

  const loadDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await EvidenceMalwareService.getQuarantineDashboard(getAuthToken());
      setSummary(data);
    } catch (err: any) {
      setError(err.message || "Failed to load quarantine telemetry.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, [token]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const file = files[0];
    setUploading(true);
    setUploadError(null);
    setUploadResult(null);

    try {
      const result = await EvidenceMalwareService.uploadEvidence(file, undefined, getAuthToken());
      setUploadResult(result);
      await loadDashboard();
    } catch (err: any) {
      setUploadError(err.message || "Evidence upload and malware inspection failed.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-900/60 p-6 rounded-xl border border-slate-800">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold text-slate-100">
              Antivirus & Secure Evidence Upload Protection
            </h2>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              Phase 12.9
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            ClamAV TCP daemon streaming, YARA static rule inspection, magic byte header validation & MinIO quarantine bucket staging.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg shadow-sm cursor-pointer transition-colors">
            {uploading ? "Inspecting Payload..." : "+ Upload Evidence File"}
            <input
              type="file"
              onChange={handleFileUpload}
              disabled={uploading}
              className="hidden"
            />
          </label>
        </div>
      </div>

      {/* Upload Inspection Status Alert */}
      {uploadResult && (
        <div
          className={`p-4 rounded-xl border ${
            uploadResult.status === "CLEAN"
              ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-300"
              : "bg-rose-500/10 border-rose-500/20 text-rose-300"
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="font-semibold text-sm">
              Payload Status: {uploadResult.status}
            </div>
            <span className="font-mono text-xs text-slate-400">
              ID: {uploadResult.evidence_id.slice(0, 8)}...
            </span>
          </div>
          <p className="text-xs mt-1">{uploadResult.message}</p>
          <div className="font-mono text-xs text-slate-400 mt-1">
            Staged Path: {uploadResult.quarantine_path}
          </div>
        </div>
      )}

      {uploadError && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm">
          ⚠️ Upload Rejected: {uploadError}
        </div>
      )}

      {/* Quarantine Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 bg-slate-900/50 border border-slate-800 rounded-xl">
          <div className="text-xs text-slate-400 font-medium uppercase tracking-wider">
            Total Inspected Files
          </div>
          <div className="mt-2 text-2xl font-bold text-slate-100">
            {summary?.total_scanned || 0}
          </div>
          <div className="text-xs text-slate-500 mt-1">Magic Byte + ClamAV + YARA</div>
        </div>

        <div className="p-4 bg-slate-900/50 border border-slate-800 rounded-xl">
          <div className="text-xs text-slate-400 font-medium uppercase tracking-wider">
            Verified Clean
          </div>
          <div className="mt-2 text-2xl font-bold text-emerald-400">
            {summary?.clean_count || 0}
          </div>
          <div className="text-xs text-slate-500 mt-1">Eligible for production bucket</div>
        </div>

        <div className="p-4 bg-slate-900/50 border border-slate-800 rounded-xl">
          <div className="text-xs text-slate-400 font-medium uppercase tracking-wider">
            Isolated in Quarantine
          </div>
          <div className="mt-2 text-2xl font-bold text-amber-400">
            {summary?.quarantined_count || 0}
          </div>
          <div className="text-xs text-slate-500 mt-1">Held in vulnova-quarantine-bucket</div>
        </div>

        <div className="p-4 bg-slate-900/50 border border-slate-800 rounded-xl">
          <div className="text-xs text-slate-400 font-medium uppercase tracking-wider">
            Malware Threats Intercepted
          </div>
          <div className="mt-2 text-2xl font-bold text-rose-400">
            {summary?.malware_detected_count || 0}
          </div>
          <div className="text-xs text-slate-500 mt-1">Blocked execution attempts</div>
        </div>
      </div>

      {/* Threat Detections Table */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex justify-between items-center">
          <h3 className="font-semibold text-slate-200">
            Security Quarantine & Malware Alert Log
          </h3>
          <button
            onClick={loadDashboard}
            className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
          >
            Refresh Telemetry
          </button>
        </div>

        {loading ? (
          <div className="p-8 text-center text-slate-400">Loading quarantine log...</div>
        ) : error ? (
          <div className="p-8 text-center text-rose-400">{error}</div>
        ) : !summary?.active_threats || summary.active_threats.length === 0 ? (
          <div className="p-8 text-center text-slate-500">
            No malware threats detected in quarantine storage. All uploads clean.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-950/60 text-slate-400 text-xs uppercase border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3">Threat Rule / Signature</th>
                  <th className="px-4 py-3">Engine</th>
                  <th className="px-4 py-3">Severity</th>
                  <th className="px-4 py-3">Timestamp</th>
                  <th className="px-4 py-3">Scan ID</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-300">
                {summary.active_threats.map((threat) => (
                  <tr key={threat.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-4 py-3 font-medium text-rose-400 font-mono text-xs">
                      {threat.rule_name}
                    </td>
                    <td className="px-4 py-3 text-xs uppercase font-mono text-slate-300">
                      {threat.engine}
                    </td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 rounded text-xs font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30">
                        {threat.severity}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">
                      {new Date(threat.timestamp).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-xs font-mono text-slate-500">
                      {threat.scan_id.slice(0, 8)}...
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
