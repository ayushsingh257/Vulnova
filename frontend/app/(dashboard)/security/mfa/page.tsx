"use client";

import React, { useEffect, useState } from "react";
import { ShieldCheck, RefreshCw } from "lucide-react";
import { DashboardLayout } from "@/components/dashboard/dashboard-layout";
import { MFAService, MFAStatusResponse, MFASetupResponse } from "@/services/mfa.service";
import { MFAStatusCard } from "@/components/security/MFAStatusCard";
import { MFASetupWizard } from "@/components/security/MFASetupWizard";
import { RecoveryCodesModal } from "@/components/security/RecoveryCodesModal";

export default function MFADashboardPage() {
  const [statusData, setStatusData] = useState<MFAStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [setupData, setSetupData] = useState<MFASetupResponse | null>(null);
  const [showDisableModal, setShowDisableModal] = useState(false);
  const [disablePassword, setDisablePassword] = useState("");
  const [disableCode, setDisableCode] = useState("");
  const [disableError, setDisableError] = useState<string | null>(null);
  const [newRecoveryCodes, setNewRecoveryCodes] = useState<string[] | null>(null);

  const fetchStatus = async () => {
    setLoading(true);
    try {
      const data = await MFAService.getStatus();
      setStatusData(data);
    } catch (err) {
      console.error("Failed to fetch MFA status:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const handleStartSetup = async () => {
    try {
      const res = await MFAService.initiateSetup();
      setSetupData(res);
    } catch (err: any) {
      alert(err.message || "Failed to initiate MFA setup.");
    }
  };

  const handleDisableMFA = async (e: React.FormEvent) => {
    e.preventDefault();
    setDisableError(null);
    try {
      await MFAService.disableMFA(disablePassword, disableCode);
      setShowDisableModal(false);
      setDisablePassword("");
      setDisableCode("");
      await fetchStatus();
    } catch (err: any) {
      setDisableError(err.message || "Failed to disable MFA.");
    }
  };

  const handleRegenerateCodes = async () => {
    const password = prompt("Enter your current password to regenerate backup codes:");
    if (!password) return;
    const code = prompt("Enter 6-digit OTP from your authenticator app:");
    if (!code) return;

    try {
      const res = await MFAService.regenerateRecoveryCodes(password, code);
      setNewRecoveryCodes(res.recovery_codes);
      await fetchStatus();
    } catch (err: any) {
      alert(err.message || "Failed to regenerate recovery codes.");
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-8 max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-zinc-800 pb-6">
          <div className="flex items-center space-x-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-600/20 border border-amber-500/40 text-amber-400 shadow-md">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-black tracking-tight text-white">
                Multi-Factor Authentication (MFA / TOTP)
              </h1>
              <p className="text-xs text-zinc-400 mt-0.5">
                Manage account authentication security, authenticator apps, and single-use emergency backup recovery codes
              </p>
            </div>
          </div>

          <button
            onClick={fetchStatus}
            className="p-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white transition-colors"
            title="Refresh Status"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </div>

        {/* Setup Wizard or Status Card */}
        {setupData ? (
          <MFASetupWizard
            setupData={setupData}
            onComplete={() => {
              setSetupData(null);
              fetchStatus();
            }}
            onCancel={() => setSetupData(null)}
          />
        ) : loading ? (
          <div className="text-center py-12 text-zinc-500 text-sm">
            Loading MFA authentication status...
          </div>
        ) : statusData ? (
          <MFAStatusCard
            mfaEnabled={statusData.mfa_enabled}
            mfaVerifiedAt={statusData.mfa_verified_at}
            mfaLastUsedAt={statusData.mfa_last_used_at}
            backupCodesRemaining={statusData.backup_codes_remaining}
            onInitiateSetup={handleStartSetup}
            onDisable={() => setShowDisableModal(true)}
            onRegenerateCodes={handleRegenerateCodes}
          />
        ) : null}

        {/* Disable Modal */}
        {showDisableModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
            <div className="w-full max-w-md bg-zinc-950 border border-zinc-800 rounded-xl p-6 space-y-4 shadow-2xl">
              <h3 className="text-base font-bold text-white">Disable Multi-Factor Authentication</h3>
              <p className="text-xs text-zinc-400">
                To confirm disabling MFA, enter your account password and a valid 6-digit OTP code.
              </p>

              {disableError && (
                <div className="p-3 rounded bg-red-950/40 border border-red-800 text-xs text-red-300">
                  {disableError}
                </div>
              )}

              <form onSubmit={handleDisableMFA} className="space-y-4">
                <div>
                  <label className="text-xs font-bold text-zinc-300 block mb-1">Current Password</label>
                  <input
                    type="password"
                    value={disablePassword}
                    onChange={(e) => setDisablePassword(e.target.value)}
                    required
                    className="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-800 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="text-xs font-bold text-zinc-300 block mb-1">6-Digit OTP Code</label>
                  <input
                    type="text"
                    maxLength={6}
                    value={disableCode}
                    onChange={(e) => setDisableCode(e.target.value)}
                    required
                    className="w-full px-3 py-2 rounded-lg bg-zinc-900 border border-zinc-800 text-xs text-white text-center font-mono tracking-widest"
                  />
                </div>

                <div className="flex space-x-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setShowDisableModal(false)}
                    className="flex-1 py-2 rounded-lg bg-zinc-900 border border-zinc-800 text-xs font-bold text-zinc-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="flex-1 py-2 rounded-lg bg-red-600 font-bold text-xs text-white hover:bg-red-500"
                  >
                    Confirm Disable
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Display New Backup Codes after regeneration */}
        {newRecoveryCodes && (
          <RecoveryCodesModal
            recoveryCodes={newRecoveryCodes}
            onClose={() => setNewRecoveryCodes(null)}
          />
        )}
      </div>
    </DashboardLayout>
  );
}
