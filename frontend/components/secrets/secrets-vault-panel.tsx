"use client";

import React, { useEffect, useState } from "react";
import {
  KMSHealth,
  SecretDecrypted,
  SecretResponse,
  SecretRotationStatus,
  SecretsVaultService,
} from "../../services/secrets_vault.service";

interface SecretsVaultPanelProps {
  token?: string;
  userRole?: string;
}

export function SecretsVaultPanel({ token, userRole = "ADMIN" }: SecretsVaultPanelProps) {
  const [secrets, setSecrets] = useState<SecretResponse[]>([]);
  const [rotationStatus, setRotationStatus] = useState<SecretRotationStatus | null>(null);
  const [kmsHealthList, setKmsHealthList] = useState<KMSHealth[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Decrypted modal state
  const [revealedSecret, setRevealedSecret] = useState<SecretDecrypted | null>(null);
  const [revealingId, setRevealingId] = useState<string | null>(null);

  // New secret form state
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [secretName, setSecretName] = useState("");
  const [secretType, setSecretType] = useState<"INTEGRATION_TOKEN" | "API_KEY" | "CLOUD_CREDENTIAL" | "CERTIFICATE" | "GENERIC">("GENERIC");
  const [plaintextValue, setPlaintextValue] = useState("");
  const [rotationDays, setRotationDays] = useState(90);

  const getAuthToken = React.useCallback(() => {
    if (token) return token;
    if (typeof window !== "undefined") {
      return localStorage.getItem("token") || undefined;
    }
    return undefined;
  }, [token]);

  const loadData = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const authToken = getAuthToken();
      const [secList, rotStatus, health] = await Promise.all([
        SecretsVaultService.listSecrets(undefined, 0, 50, authToken),
        SecretsVaultService.getRotationStatus(authToken),
        SecretsVaultService.getKmsHealth(authToken),
      ]);
      setSecrets(secList);
      setRotationStatus(rotStatus);
      setKmsHealthList(health);
    } catch (err: any) {
      setError(err.message || "Failed to load secrets vault data.");
    } finally {
      setLoading(false);
    }
  }, [getAuthToken]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreateSecret = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!secretName || !plaintextValue) return;

    try {
      await SecretsVaultService.storeSecret(
        {
          secret_name: secretName,
          secret_type: secretType,
          plaintext_value: plaintextValue,
          rotation_interval_days: rotationDays,
        },
        getAuthToken()
      );
      setShowCreateModal(false);
      setSecretName("");
      setPlaintextValue("");
      await loadData();
    } catch (err: any) {
      alert(`Error storing secret: ${err.message}`);
    }
  };

  const handleReveal = async (id: string) => {
    setRevealingId(id);
    try {
      const res = await SecretsVaultService.accessSecretPlaintext(id, getAuthToken());
      setRevealedSecret(res);
    } catch (err: any) {
      alert(`Access denied: ${err.message}`);
    } finally {
      setRevealingId(null);
    }
  };

  const handleRotate = async (id: string) => {
    if (!confirm("Are you sure you want to rotate this secret with a fresh Data Encryption Key (DEK)?")) return;
    try {
      await SecretsVaultService.rotateSecret(id, { reason: "Admin triggered on-demand rotation" }, getAuthToken());
      await loadData();
    } catch (err: any) {
      alert(`Rotation failed: ${err.message}`);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to permanently delete this secret? This action is irreversible.")) return;
    try {
      await SecretsVaultService.deleteSecret(id, getAuthToken());
      await loadData();
    } catch (err: any) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-slate-900/60 p-6 rounded-xl border border-slate-800">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold text-slate-100">Enterprise Secrets Vault & KMS Governance</h2>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Phase 12.8
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Zero-trust envelope encryption (AES-256-GCM) with external Key Management Systems & automated 90-day rotation.
          </p>
        </div>
        {userRole === "ADMIN" && (
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg shadow-sm transition-colors"
          >
            + Store Secret
          </button>
        )}
      </div>

      {/* KMS Health & Rotation Posture Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 bg-slate-900/50 border border-slate-800 rounded-xl">
          <div className="text-xs text-slate-400 font-medium uppercase tracking-wider">Active KMS Provider</div>
          <div className="mt-2 flex items-center justify-between">
            <span className="text-lg font-bold text-slate-100 uppercase">{rotationStatus?.active_provider || "LOCAL"}</span>
            <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-500/20 text-emerald-300">
              HEALTHY
            </span>
          </div>
          <div className="text-xs text-slate-500 mt-1">External Envelope KEK</div>
        </div>

        <div className="p-4 bg-slate-900/50 border border-slate-800 rounded-xl">
          <div className="text-xs text-slate-400 font-medium uppercase tracking-wider">Total Managed Secrets</div>
          <div className="mt-2 text-2xl font-bold text-slate-100">{rotationStatus?.total_secrets || 0}</div>
          <div className="text-xs text-slate-500 mt-1">Encrypted via AES-256 DEKs</div>
        </div>

        <div className="p-4 bg-slate-900/50 border border-slate-800 rounded-xl">
          <div className="text-xs text-slate-400 font-medium uppercase tracking-wider">Due in 30 Days</div>
          <div className="mt-2 text-2xl font-bold text-amber-400">{rotationStatus?.due_in_30_days || 0}</div>
          <div className="text-xs text-slate-500 mt-1">Scheduled for auto-rotation</div>
        </div>

        <div className="p-4 bg-slate-900/50 border border-slate-800 rounded-xl">
          <div className="text-xs text-slate-400 font-medium uppercase tracking-wider">Overdue Rotations</div>
          <div className="mt-2 text-2xl font-bold text-rose-400">{rotationStatus?.overdue_rotations || 0}</div>
          <div className="text-xs text-slate-500 mt-1">Exceeding 90-day SLA</div>
        </div>
      </div>

      {/* Secrets Table */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex justify-between items-center">
          <h3 className="font-semibold text-slate-200">Encrypted Secrets Repository</h3>
          <button
            onClick={loadData}
            className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
          >
            Refresh Telemetry
          </button>
        </div>

        {loading ? (
          <div className="p-8 text-center text-slate-400">Loading secrets vault...</div>
        ) : error ? (
          <div className="p-8 text-center text-rose-400">{error}</div>
        ) : secrets.length === 0 ? (
          <div className="p-8 text-center text-slate-500">No secrets found in this organization.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-950/60 text-slate-400 text-xs uppercase border-b border-slate-800">
                <tr>
                  <th className="px-4 py-3">Secret Name</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Provider</th>
                  <th className="px-4 py-3">Masked Preview</th>
                  <th className="px-4 py-3">Key Version</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Next Rotation</th>
                  <th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800 text-slate-300">
                {secrets.map((sec) => (
                  <tr key={sec.id} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-4 py-3 font-medium text-slate-100">{sec.secret_name}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 rounded text-xs font-mono bg-slate-800 text-slate-300">
                        {sec.secret_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs uppercase font-mono text-slate-400">{sec.provider}</td>
                    <td className="px-4 py-3 font-mono text-xs text-slate-400">{sec.masked_value}</td>
                    <td className="px-4 py-3 font-mono text-xs text-indigo-400">v{sec.key_version}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                          sec.status === "ACTIVE"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : sec.status === "ROTATED"
                            ? "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                            : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                        }`}
                      >
                        {sec.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">
                      {sec.next_rotation_due
                        ? new Date(sec.next_rotation_due).toLocaleDateString()
                        : "Every 90d"}
                    </td>
                    <td className="px-4 py-3 text-right space-x-2">
                      <button
                        onClick={() => handleReveal(sec.id)}
                        disabled={revealingId === sec.id}
                        className="text-xs text-emerald-400 hover:text-emerald-300 font-medium"
                      >
                        {revealingId === sec.id ? "Decrypting..." : "Access"}
                      </button>
                      <button
                        onClick={() => handleRotate(sec.id)}
                        className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
                      >
                        Rotate
                      </button>
                      <button
                        onClick={() => handleDelete(sec.id)}
                        className="text-xs text-rose-400 hover:text-rose-300 font-medium"
                      >
                        Revoke
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Reveal Plaintext Modal */}
      {revealedSecret && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-lg w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-slate-100">Authorized Secret Access</h3>
            <p className="text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 p-2.5 rounded">
              ⚠️ Plaintext secret accessed. This access event is permanently recorded in the immutable audit log.
            </p>
            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase">Secret Name</label>
              <div className="text-slate-100 font-mono text-sm mt-1">{revealedSecret.secret_name}</div>
            </div>
            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase">Plaintext Value</label>
              <div className="bg-slate-950 p-3 rounded border border-slate-800 text-emerald-400 font-mono text-sm break-all select-all mt-1">
                {revealedSecret.plaintext_value}
              </div>
            </div>
            <div className="flex justify-end pt-2">
              <button
                onClick={() => setRevealedSecret(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-semibold rounded-lg"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Store Secret Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-700 rounded-xl max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-slate-100">Store Envelope-Encrypted Secret</h3>
            <form onSubmit={handleCreateSecret} className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-slate-400">Secret Name</label>
                <input
                  type="text"
                  required
                  value={secretName}
                  onChange={(e) => setSecretName(e.target.value)}
                  placeholder="e.g. prod_aws_scanner_key"
                  className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-400">Secret Type</label>
                <select
                  value={secretType}
                  onChange={(e) => setSecretType(e.target.value as any)}
                  className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
                >
                  <option value="GENERIC">GENERIC</option>
                  <option value="INTEGRATION_TOKEN">INTEGRATION_TOKEN</option>
                  <option value="API_KEY">API_KEY</option>
                  <option value="CLOUD_CREDENTIAL">CLOUD_CREDENTIAL</option>
                  <option value="CERTIFICATE">CERTIFICATE</option>
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-400">Plaintext Secret Value</label>
                <textarea
                  required
                  rows={3}
                  value={plaintextValue}
                  onChange={(e) => setPlaintextValue(e.target.value)}
                  placeholder="Paste secret or token here..."
                  className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded text-slate-100 text-sm font-mono focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="text-xs font-semibold text-slate-400">Auto-Rotation Interval (Days)</label>
                <input
                  type="number"
                  min={1}
                  max={365}
                  value={rotationDays}
                  onChange={(e) => setRotationDays(Number(e.target.value))}
                  className="w-full mt-1 px-3 py-2 bg-slate-950 border border-slate-800 rounded text-slate-100 text-sm focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-semibold rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg"
                >
                  Encrypt & Save
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
