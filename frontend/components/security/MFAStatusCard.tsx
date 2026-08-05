"use client";

import React from "react";
import { ShieldCheck, ShieldOff, KeyRound, Clock, AlertTriangle } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface MFAStatusCardProps {
  mfaEnabled: boolean;
  mfaVerifiedAt?: string;
  mfaLastUsedAt?: string;
  backupCodesRemaining: number;
  onInitiateSetup?: () => void;
  onDisable?: () => void;
  onRegenerateCodes?: () => void;
}

export const MFAStatusCard: React.FC<MFAStatusCardProps> = ({
  mfaEnabled,
  mfaVerifiedAt,
  mfaLastUsedAt,
  backupCodesRemaining,
  onInitiateSetup,
  onDisable,
  onRegenerateCodes,
}) => {
  return (
    <Card className="border-zinc-800 bg-zinc-950/80 backdrop-blur-md">
      <CardHeader className="flex flex-row items-center justify-between pb-4 border-b border-zinc-800">
        <div className="flex items-center space-x-3">
          <div
            className={`flex h-10 w-10 items-center justify-center rounded-xl border shadow-md ${
              mfaEnabled
                ? "bg-emerald-950/40 border-emerald-500/40 text-emerald-400"
                : "bg-amber-950/40 border-amber-500/40 text-amber-400"
            }`}
          >
            {mfaEnabled ? <ShieldCheck className="h-6 w-6" /> : <ShieldOff className="h-6 w-6" />}
          </div>
          <div>
            <CardTitle className="text-base font-bold text-white">
              Multi-Factor Authentication (MFA / TOTP)
            </CardTitle>
            <p className="text-xs text-zinc-400 mt-0.5">
              Protect account logins using time-based one-time passcodes (RFC 6238)
            </p>
          </div>
        </div>

        <Badge variant={mfaEnabled ? "success" : "warning"}>
          {mfaEnabled ? "ENABLED" : "NOT ENABLED"}
        </Badge>
      </CardHeader>

      <CardContent className="pt-6 space-y-6">
        {mfaEnabled ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs font-mono">
              {/* Verified Timestamp */}
              <div className="p-3 rounded-lg bg-zinc-900 border border-zinc-800 space-y-1">
                <div className="flex items-center space-x-1.5 text-zinc-400">
                  <Clock className="h-3.5 w-3.5 text-amber-400" />
                  <span>Activated On</span>
                </div>
                <div className="text-white font-bold truncate">
                  {mfaVerifiedAt ? new Date(mfaVerifiedAt).toLocaleDateString() : "Active"}
                </div>
              </div>

              {/* Last Used */}
              <div className="p-3 rounded-lg bg-zinc-900 border border-zinc-800 space-y-1">
                <div className="flex items-center space-x-1.5 text-zinc-400">
                  <Clock className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Last Verification</span>
                </div>
                <div className="text-white font-bold truncate">
                  {mfaLastUsedAt ? new Date(mfaLastUsedAt).toLocaleString() : "Never"}
                </div>
              </div>

              {/* Backup codes remaining */}
              <div className="p-3 rounded-lg bg-zinc-900 border border-zinc-800 space-y-1">
                <div className="flex items-center space-x-1.5 text-zinc-400">
                  <KeyRound className="h-3.5 w-3.5 text-amber-400" />
                  <span>Backup Codes</span>
                </div>
                <div className="text-white font-bold">
                  {backupCodesRemaining} codes remaining
                </div>
              </div>
            </div>

            <div className="flex flex-wrap gap-3 pt-2">
              <button
                onClick={onRegenerateCodes}
                className="px-4 py-2 rounded-lg bg-zinc-900 border border-zinc-800 text-xs font-bold text-zinc-200 hover:bg-zinc-800 transition-colors"
              >
                Regenerate Backup Codes
              </button>
              <button
                onClick={onDisable}
                className="px-4 py-2 rounded-lg bg-red-950/40 border border-red-800/60 text-xs font-bold text-red-300 hover:bg-red-900/60 transition-colors"
              >
                Disable MFA
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="p-4 rounded-lg bg-amber-950/20 border border-amber-800/40 text-xs text-amber-300 flex items-start space-x-3">
              <AlertTriangle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold block mb-0.5">Account Security Warning</span>
                Your account is currently protected by password authentication only. Enabling Multi-Factor Authentication adds an essential layer of security against credential stuffing and brute-force attacks.
              </div>
            </div>

            <button
              onClick={onInitiateSetup}
              className="px-5 py-2.5 rounded-lg bg-amber-600 font-bold text-xs text-white hover:bg-amber-500 transition-colors shadow-md flex items-center space-x-2"
            >
              <ShieldCheck className="h-4 w-4" />
              <span>Enable MFA / TOTP</span>
            </button>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
