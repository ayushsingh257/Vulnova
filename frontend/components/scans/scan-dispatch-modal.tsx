"use client";

import * as React from "react";
import { Play, ShieldCheck, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { ScansService } from "@/services/scans.service";

export function ScanDispatchModal({
  isOpen,
  onClose,
  onScanDispatched,
}: {
  isOpen: boolean;
  onClose: () => void;
  onScanDispatched?: () => void;
}) {
  const [profile, setProfile] = React.useState("FULL_RECON");
  const [priority, setPriority] = React.useState("DEFAULT");
  const [consent, setConsent] = React.useState(false);
  const [loading, setLoading] = React.useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!consent) return;

    setLoading(true);
    try {
      await ScansService.dispatchScan({
        target_id: "3fa85f64-5717-4562-b3fc-2c963f66afa6",
        scan_profile: profile,
        priority_queue: priority,
        legal_consent_confirmed: true,
      });
      if (onScanDispatched) onScanDispatched();
      onClose();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <Card className="w-full max-w-lg border-zinc-800 bg-zinc-950 text-zinc-100 shadow-2xl">
        <CardHeader className="flex flex-row items-center justify-between border-b border-zinc-800 pb-4">
          <div className="flex items-center space-x-2">
            <Play className="h-5 w-5 text-red-500" />
            <CardTitle className="text-lg font-bold">Dispatch Vulnerability Scan</CardTitle>
          </div>
          <button onClick={onClose} className="text-zinc-400 hover:text-white transition-colors">
            <X className="h-5 w-5" />
          </button>
        </CardHeader>

        <CardContent className="space-y-4 pt-4 text-xs">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="font-semibold text-zinc-300">Target Asset Scope</label>
              <select className="w-full p-2.5 rounded-lg border border-zinc-800 bg-zinc-900 text-zinc-200 focus:outline-none focus:border-red-500">
                <option>Production API Gateway (https://a***.s***.e***.com)</option>
                <option>Auth Service Staging (https://a***.s***.domain.org)</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="font-semibold text-zinc-300">Scan Profile Policy</label>
              <select
                value={profile}
                onChange={(e) => setProfile(e.target.value)}
                className="w-full p-2.5 rounded-lg border border-zinc-800 bg-zinc-900 text-zinc-200 focus:outline-none focus:border-red-500"
              >
                <option value="FULL_RECON">FULL_RECON (Comprehensive Recon & DAST)</option>
                <option value="LIGHTWEIGHT_DAST">LIGHTWEIGHT_DAST (Fast Port & Header Audit)</option>
                <option value="COMPLIANCE_AUDIT">COMPLIANCE_AUDIT (OWASP ASVS v4.0 Check)</option>
              </select>
            </div>

            <div className="p-3 rounded-xl border border-red-900/40 bg-red-950/20 space-y-2">
              <div className="flex items-center space-x-2 text-red-400 font-bold">
                <ShieldCheck className="h-4 w-4" />
                <span>Authorized Assessment Contract Consent</span>
              </div>
              <p className="text-[11px] text-zinc-400 leading-relaxed">
                You certify that you hold explicit legal consent to perform vulnerability testing against this target scope under CFAA governance rules.
              </p>
              <label className="flex items-center space-x-2 pt-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={consent}
                  onChange={(e) => setConsent(e.target.checked)}
                  className="rounded border-zinc-700 bg-zinc-900 text-red-500 focus:ring-red-500"
                />
                <span className="text-[11px] font-semibold text-zinc-200">
                  I confirm target assessment authorization
                </span>
              </label>
            </div>

            <div className="flex items-center justify-end space-x-3 pt-2">
              <Button variant="outline" size="sm" type="button" onClick={onClose}>
                Cancel
              </Button>
              <Button variant="primary" size="sm" type="submit" disabled={!consent || loading}>
                {loading ? "Dispatching..." : "Launch Scan Execution"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
