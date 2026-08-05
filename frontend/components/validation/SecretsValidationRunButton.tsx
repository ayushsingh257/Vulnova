"use client";

import React, { useState } from "react";
import { Play, Loader2 } from "lucide-react";
import { SecretsValidationService, SecretsValidationSuiteResponse } from "@/services/secrets_validation.service";

interface SecretsValidationRunButtonProps {
  onRunComplete: (result: SecretsValidationSuiteResponse) => void;
}

export const SecretsValidationRunButton: React.FC<SecretsValidationRunButtonProps> = ({
  onRunComplete,
}) => {
  const [running, setRunning] = useState(false);

  const handleRun = async () => {
    setRunning(true);
    try {
      const res = await SecretsValidationService.runSuite();
      onRunComplete(res);
    } catch (err) {
      console.error("Failed to run secrets validation suite:", err);
    } finally {
      setRunning(false);
    }
  };

  return (
    <button
      onClick={handleRun}
      disabled={running}
      className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-purple-600 font-bold text-xs text-white hover:bg-purple-500 transition-colors disabled:opacity-50"
    >
      {running ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Evaluating Cryptographic Assertions...</span>
        </>
      ) : (
        <>
          <Play className="h-4 w-4 fill-current" />
          <span>Run Secrets Audit</span>
        </>
      )}
    </button>
  );
};
