"use client";

import React, { useState } from "react";
import { Copy, Check, QrCode } from "lucide-react";

interface QRCodeDisplayProps {
  qrCodeBase64: string;
  secret: string;
  provisioningUri: string;
}

export const QRCodeDisplay: React.FC<QRCodeDisplayProps> = ({
  qrCodeBase64,
  secret,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopySecret = () => {
    navigator.clipboard.writeText(secret);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="flex flex-col items-center space-y-4 text-center p-6 rounded-xl bg-zinc-900/80 border border-zinc-800">
      <div className="flex items-center space-x-2 text-xs font-bold text-amber-400 uppercase tracking-wider">
        <QrCode className="h-4 w-4" />
        <span>Scan Authenticator QR Code</span>
      </div>

      {/* QR Code Image */}
      <div className="p-3 bg-white rounded-xl shadow-lg border border-zinc-200">
        <img
          src={qrCodeBase64}
          alt="MFA QR Code"
          className="h-44 w-44 object-contain"
        />
      </div>

      <p className="text-xs text-zinc-400 max-w-xs">
        Scan this QR code using Google Authenticator, Microsoft Authenticator, Authy, or 1Password.
      </p>

      {/* Manual Entry Key */}
      <div className="w-full max-w-xs space-y-1">
        <span className="text-[11px] font-mono text-zinc-400">Cannot scan? Enter key manually:</span>
        <div className="flex items-center justify-between p-2.5 rounded-lg bg-zinc-950 border border-zinc-800 text-xs font-mono text-amber-300">
          <span className="truncate tracking-widest">{secret}</span>
          <button
            onClick={handleCopySecret}
            className="p-1 rounded text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors ml-2 shrink-0"
            title="Copy Secret Key"
          >
            {copied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
          </button>
        </div>
      </div>
    </div>
  );
};
