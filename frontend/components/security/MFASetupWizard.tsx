"use client";

import React, { useState } from "react";
import { MFAService, MFASetupResponse } from "@/services/mfa.service";
import { QRCodeDisplay } from "./QRCodeDisplay";
import { OTPVerificationForm } from "./OTPVerificationForm";
import { RecoveryCodesModal } from "./RecoveryCodesModal";

interface MFASetupWizardProps {
  setupData: MFASetupResponse;
  onComplete: () => void;
  onCancel: () => void;
}

export const MFASetupWizard: React.FC<MFASetupWizardProps> = ({
  setupData,
  onComplete,
  onCancel,
}) => {
  const [step, setStep] = useState<"qr" | "recovery">("qr");

  const handleVerify = async (code: string) => {
    await MFAService.verifySetup(code);
    setStep("recovery");
  };

  return (
    <div className="p-6 rounded-xl bg-zinc-950 border border-zinc-800 space-y-6 max-w-lg mx-auto">
      <div className="border-b border-zinc-800 pb-4">
        <h2 className="text-lg font-bold text-white">Enable Multi-Factor Authentication</h2>
        <p className="text-xs text-zinc-400 mt-0.5">Step 1: Scan QR code and verify authenticator code</p>
      </div>

      <QRCodeDisplay
        qrCodeBase64={setupData.qr_code_base64}
        secret={setupData.secret}
        provisioningUri={setupData.provisioning_uri}
      />

      <div className="border-t border-zinc-800 pt-4 space-y-3">
        <span className="text-xs font-bold text-zinc-300 block text-center">
          Enter 6-digit code from your authenticator app to complete setup:
        </span>
        <OTPVerificationForm onVerify={handleVerify} buttonText="Activate MFA" />
      </div>

      <button
        onClick={onCancel}
        className="w-full py-2 rounded-lg bg-zinc-900 border border-zinc-800 text-xs font-bold text-zinc-400 hover:text-white"
      >
        Cancel Setup
      </button>

      {step === "recovery" && (
        <RecoveryCodesModal
          recoveryCodes={setupData.recovery_codes}
          onClose={onComplete}
        />
      )}
    </div>
  );
};
