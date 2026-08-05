"use client";

import React, { useState } from "react";
import { Play, Loader2 } from "lucide-react";
import { ThreatValidationService, ThreatValidationSuiteResponse } from "@/services/threat_validation.service";

interface ThreatValidationRunButtonProps {
  onRunComplete: (result: ThreatValidationSuiteResponse) => void;
}

export const ThreatValidationRunButton: React.FC<ThreatValidationRunButtonProps> = ({
  onRunComplete,
}) => {
  const [running, setRunning] = useState(false);

  const handleRun = async () => {
    setRunning(true);
    try {
      const res = await ThreatValidationService.runSuite();
      onRunComplete(res);
    } catch (err) {
      console.error("Failed to run threat validation suite:", err);
    } finally {
      setRunning(false);
    }
  };

  return (
    <button
      onClick={handleRun}
      disabled={running}
      className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-orange-600 font-bold text-xs text-white hover:bg-orange-500 transition-colors disabled:opacity-50"
    >
      {running ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Evaluating STRIDE Threat Model...</span>
        </>
      ) : (
        <>
          <Play className="h-4 w-4 fill-current" />
          <span>Run STRIDE Audit</span>
        </>
      )}
    </button>
  );
};
