"use client";

import * as React from "react";
import { AlertTriangle, CheckCircle, Play, ShieldCheck, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { ScansService } from "@/services/scans.service";
import { TargetAuthorizationService } from "@/services/target_authorization.service";

export function ScanDispatchModal({
  isOpen,
  onClose,
  onScanDispatched,
  targetId = "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  isVerified: initialVerified = false,
}: {
  isOpen: boolean;
  onClose: () => void;
  onScanDispatched?: () => void;
  targetId?: string;
  isVerified?: boolean;
}) {
  const [profile, setProfile] = React.useState("FULL_RECON");
  const [priority, setPriority] = React.useState("DEFAULT");
  const [consent, setConsent] = React.useState(false);
  const [loading, setLoading] = React.useState(false);
  const [isVerified, setIsVerified] = React.useState(initialVerified);
  const [verifying, setVerifying] = React.useState(false);
  const [verificationMessage, setVerificationMessage] = React.useState("");

  if (!isOpen) return null;

  const handleVerifyOwnership = async () => {
    setVerifying(true);
    setVerificationMessage("");
    try {
      const res = await TargetAuthorizationService.verifyTarget(targetId, "DNS_TXT");
      if (res.verified) {
        setIsVerified(true);
        setVerificationMessage("✅ Target ownership verified successfully!");
      } else {
        setVerificationMessage(`❌ Verification failed: ${res.message}`);
      }
    } catch (err: any) {
      setVerificationMessage(`❌ Verification error: ${err.message || "Failed to query verification"}`);
    } finally {
      setVerifying(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!consent || !isVerified) return;

    setLoading(true);
    try {
      await ScansService.dispatchScan({
        target_id: targetId,
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
                <option>Production API Gateway (example.com)</option>
                <option>Auth Service Staging (staging.example.com)</option>
              </select>
            </div>

            {/* Target Ownership Verification Banner */}
            {!isVerified ? (
              <div className="p-3 rounded-xl border border-yellow-900/60 bg-yellow-950/30 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2 text-yellow-400 font-bold">
                    <AlertTriangle className="h-4 w-4" />
                    <span>Verification: ❌ Not Verified</span>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleVerifyOwnership}
                    disabled={verifying}
                    className="text-xs border-yellow-700 text-yellow-300 hover:bg-yellow-900/50"
                  >
                    {verifying ? "Verifying..." : "Verify Ownership"}
                  </Button>
                </div>
                <p className="text-[11px] text-yellow-200/80">
                  Target ownership verification required before scanning. Add a DNS TXT record for <code className="text-yellow-100 bg-yellow-900/40 px-1 py-0.5 rounded">_vulnova-verify.&lt;domain&gt;</code> to verify ownership.
                </p>
                {verificationMessage && (
                  <p className="text-[11px] font-semibold text-yellow-300 pt-1">{verificationMessage}</p>
                )}
              </div>
            ) : (
              <div className="p-3 rounded-xl border border-emerald-900/40 bg-emerald-950/20 flex items-center justify-between">
                <div className="flex items-center space-x-2 text-emerald-400 font-bold">
                  <CheckCircle className="h-4 w-4" />
                  <span>Target Ownership: ✅ Verified</span>
                </div>
                <span className="text-[10px] text-emerald-300 bg-emerald-900/40 px-2 py-0.5 rounded border border-emerald-800">
                  Scan Authorized
                </span>
              </div>
            )}

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
              <Button
                variant="primary"
                size="sm"
                type="submit"
                disabled={!consent || !isVerified || loading}
                title={!isVerified ? "Target ownership verification required before scanning" : ""}
              >
                {loading ? "Dispatching..." : "Launch Scan Execution"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
