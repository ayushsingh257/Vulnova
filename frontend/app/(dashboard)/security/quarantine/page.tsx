"use client";

import React from "react";
import { EvidenceSecurityPanel } from "@/components/evidence/evidence-security-panel";

export default function SecurityQuarantinePage() {
  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="border-b border-zinc-800 pb-4">
        <h1 className="text-2xl font-bold text-zinc-100">
          Security Quarantine & Evidence Protection Dashboard
        </h1>
        <p className="text-xs text-zinc-400 mt-1">
          Monitor magic byte header validation, ClamAV antivirus inspection, YARA static malware rules, and quarantine object promotion telemetry.
        </p>
      </div>

      <EvidenceSecurityPanel />
    </div>
  );
}
