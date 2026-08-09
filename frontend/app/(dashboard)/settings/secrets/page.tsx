"use client";

import React from "react";
import { SecretsVaultPanel } from "@/components/secrets/secrets-vault-panel";

export default function SettingsSecretsPage() {
  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="border-b border-zinc-800 pb-4">
        <h1 className="text-2xl font-bold text-zinc-100">
          Enterprise Secrets Vault & KMS Credential Governance
        </h1>
        <p className="text-xs text-zinc-400 mt-1">
          Manage zero-trust envelope encryption (AES-256-GCM), external Key Management Systems (KMS), automated rotation policies, and secret access governance.
        </p>
      </div>

      <SecretsVaultPanel />
    </div>
  );
}
