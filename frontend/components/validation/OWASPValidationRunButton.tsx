"use client";

import React, { useState } from "react";
import { Play, Loader2, RefreshCw } from "lucide-react";
import { OWASPValidationService, OWASPValidationSuiteResponse } from "@/services/owasp_validation.service";

interface OWASPValidationRunButtonProps {
  onRunComplete: (result: OWASPValidationSuiteResponse) => void;
}

export const OWASPValidationRunButton: React.FC<OWASPValidationRunButtonProps> = ({
  onRunComplete,
}) => {
  const [running, setRunning] = useState(false);

  const handleRun = async () => {
    setRunning(true);
    try {
      const res = await OWASPValidationService.runSuite();
      onRunComplete(res);
    } catch (err) {
      console.error("Failed to run OWASP validation suite:", err);
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
          <span>Executing OWASP Assertions...</span>
        </>
      ) : (
        <>
          <Play className="h-4 w-4 fill-current" />
          <span>Run OWASP Verification Suite</span>
        </>
      )}
    </button>
  );
};
