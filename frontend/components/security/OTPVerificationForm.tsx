"use client";

import React, { useState } from "react";
import { KeyRound, Loader2, AlertCircle } from "lucide-react";

interface OTPVerificationFormProps {
  onVerify: (code: string) => Promise<void>;
  buttonText?: string;
  placeholder?: string;
}

export const OTPVerificationForm: React.FC<OTPVerificationFormProps> = ({
  onVerify,
  buttonText = "Verify Code",
  placeholder = "000000",
}) => {
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code.trim()) return;

    setLoading(true);
    setError(null);
    try {
      await onVerify(code.trim());
    } catch (err: any) {
      setError(err.message || "Verification failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4 w-full">
      {error && (
        <div className="p-3 rounded-lg bg-red-950/40 border border-red-800/50 text-xs text-red-300 flex items-center space-x-2">
          <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
          <span>{error}</span>
        </div>
      )}

      <div className="space-y-1.5">
        <label className="text-xs font-bold text-zinc-300 flex items-center space-x-1.5">
          <KeyRound className="h-3.5 w-3.5 text-amber-400" />
          <span>6-Digit Security Code</span>
        </label>
        <input
          type="text"
          maxLength={10}
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder={placeholder}
          required
          className="w-full text-center tracking-widest text-lg font-mono px-4 py-2.5 rounded-lg bg-zinc-950 border border-zinc-800 text-amber-300 placeholder-zinc-700 focus:outline-none focus:border-amber-500 transition-colors"
        />
      </div>

      <button
        type="submit"
        disabled={loading || !code.trim()}
        className="w-full py-2.5 rounded-lg bg-amber-600 font-bold text-xs text-white hover:bg-amber-500 transition-colors disabled:opacity-50 flex items-center justify-center space-x-2"
      >
        {loading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>Verifying...</span>
          </>
        ) : (
          <span>{buttonText}</span>
        )}
      </button>
    </form>
  );
};
