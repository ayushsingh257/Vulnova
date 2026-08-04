"use client";

import React from "react";
import { SecurityOverviewAdmin } from "@/services/admin.service";

interface SecuritySettingsCardProps {
  security: SecurityOverviewAdmin;
}

export const SecuritySettingsCard: React.FC<SecuritySettingsCardProps> = ({
  security,
}) => {
  return (
    <div className="flex flex-col gap-6">
      <div className="rounded-xl border border-zinc-800 bg-zinc-950 p-6">
        <h3 className="text-lg font-bold text-zinc-100">
          Security Controls & Authentication Governance
        </h3>
        <p className="text-xs text-zinc-400 mt-1">
          Platform authentication policies, multi-factor enrollment tracking, and audit logging settings.
        </p>

        <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-3">
          {/* MFA Enrollment Visibility */}
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
            <p className="text-xs font-semibold uppercase text-zinc-400">
              MFA Enrollment Status
            </p>
            <p className="mt-2 text-2xl font-extrabold text-amber-400">
              {security.mfa_enrolled_count} / {security.total_users_count} Users
            </p>
            <span className="mt-2 inline-block rounded bg-zinc-800 px-2 py-0.5 text-[10px] text-zinc-400">
              Policy: {security.mfa_enforcement_status}
            </span>
          </div>

          {/* Session Security Policy */}
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
            <p className="text-xs font-semibold uppercase text-zinc-400">
              Session Security Policy
            </p>
            <p className="mt-2 text-sm font-bold text-emerald-400">
              {security.session_security_policy}
            </p>
            <p className="mt-1 text-[10px] text-zinc-400">
              Argon2id hashing, 15m JWT access tokens, family refresh rotation.
            </p>
          </div>

          {/* Audit Logging State */}
          <div className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-4">
            <p className="text-xs font-semibold uppercase text-zinc-400">
              Audit Event Logging
            </p>
            <p className="mt-2 text-sm font-bold text-zinc-100">
              {security.audit_logging_enabled ? "ENABLED & ACTIVE" : "DISABLED"}
            </p>
            <p className="mt-1 text-[10px] text-zinc-500 font-mono">
              Last Audit: {new Date(security.last_security_audit_at).toLocaleTimeString()}
            </p>
          </div>
        </div>

        {/* Informational Era 10 Notice */}
        <div className="mt-6 rounded-lg border border-blue-500/20 bg-blue-500/10 p-4 text-xs text-blue-300">
          <p className="font-semibold">ℹ️ Multi-Factor Authentication Governance Notice</p>
          <p className="mt-1 text-[11px] text-blue-300/80">
            Phase 7.6 provides administrative visibility into MFA enrollment states across team members. Full mandatory TOTP/MFA enforcement and hardware security key authentication will be introduced in Era 10.11.
          </p>
        </div>
      </div>
    </div>
  );
};
