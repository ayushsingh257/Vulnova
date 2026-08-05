"use client";

import React, { useState } from "react";
import { ShieldAlert, Copy, Check, Download, X } from "lucide-react";

interface RecoveryCodesModalProps {
  recoveryCodes: string[];
  onClose: () => void;
}

export const RecoveryCodesModal: React.FC<RecoveryCodesModalProps> = ({
  recoveryCodes,
  onClose,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopyAll = () => {
    const text = recoveryCodes.join("\n");
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const text = `VULNOVA SECURITY BACKUP RECOVERY CODES\nGenerated: ${new Date().toISOString()}\n\n${recoveryCodes.join("\n")}\n\nKeep these codes in a secure password manager or offline location. Each code can be used once.`;
    const element = document.createElement("a");
    const file = new Blob([text], { type: "text/plain" });
    element.href = URL.createObjectURL(file);
    element.download = "vulnova-recovery-codes.txt";
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-md bg-zinc-950 border border-zinc-800 rounded-xl p-6 space-y-6 shadow-2xl">
        <div className="flex items-start justify-between border-b border-zinc-800 pb-4">
          <div className="flex items-center space-x-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-600/20 border border-amber-500/40 text-amber-400">
              <ShieldAlert className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">Save Backup Recovery Codes</h2>
              <p className="text-xs text-zinc-400">Single-use emergency codes for account access</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded text-zinc-400 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-3 rounded-lg bg-amber-950/30 border border-amber-800/50 text-xs text-amber-300">
          ⚠️ Save these 10 backup codes immediately! If you lose access to your authenticator app, these codes are the ONLY way to recover your account.
        </div>

        {/* Codes Grid */}
        <div className="grid grid-cols-2 gap-2 font-mono text-xs p-4 rounded-xl bg-zinc-900 border border-zinc-800 text-center">
          {recoveryCodes.map((code, idx) => (
            <div key={idx} className="p-2 rounded bg-zinc-950 border border-zinc-800/80 text-amber-300">
              {code}
            </div>
          ))}
        </div>

        {/* Actions */}
        <div className="flex space-x-3">
          <button
            onClick={handleCopyAll}
            className="flex-1 py-2 rounded-lg bg-zinc-900 border border-zinc-800 text-xs font-bold text-zinc-200 hover:bg-zinc-800 flex items-center justify-center space-x-1.5"
          >
            {copied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
            <span>{copied ? "Copied All" : "Copy Codes"}</span>
          </button>
          <button
            onClick={handleDownload}
            className="flex-1 py-2 rounded-lg bg-amber-600 font-bold text-xs text-white hover:bg-amber-500 flex items-center justify-center space-x-1.5"
          >
            <Download className="h-4 w-4" />
            <span>Download .TXT</span>
          </button>
        </div>

        <button
          onClick={onClose}
          className="w-full py-2.5 rounded-lg bg-zinc-900 border border-zinc-800 text-xs font-bold text-zinc-400 hover:text-white"
        >
          I Have Saved My Recovery Codes
        </button>
      </div>
    </div>
  );
};
