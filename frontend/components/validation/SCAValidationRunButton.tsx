"use client";

import React, { useState } from "react";
import { Play, Loader2 } from "lucide-react";
import { SCAValidationService, SCAValidationSuiteResponse } from "@/services/sca_validation.service";

interface SCAValidationRunButtonProps {
  onRunComplete: (result: SCAValidationSuiteResponse) => void;
}

export const SCAValidationRunButton: React.FC<SCAValidationRunButtonProps> = ({
  onRunComplete,
}) => {
  const [running, setRunning] = useState(false);

  const handleRun = async () => {
    setRunning(true);
    try {
      const res = await SCAValidationService.runSuite();
      onRunComplete(res);
    } catch (err) {
      console.error("Failed to run dependency validation suite:", err);
    } finally {
      setRunning(false);
    }
  };

  return (
    <button
      onClick={handleRun}
      disabled={running}
      className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-blue-600 font-bold text-xs text-white hover:bg-blue-500 transition-colors disabled:opacity-50"
    >
      {running ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Evaluating Dependency Assertions...</span>
        </>
      ) : (
        <>
          <Play className="h-4 w-4 fill-current" />
          <span>Run SCA Verification</span>
        </>
      )}
    </button>
  );
};
