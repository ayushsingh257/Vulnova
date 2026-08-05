"use client";

import React, { useState } from "react";
import { Play, Loader2 } from "lucide-react";
import { APISecurityValidationService, APIValidationSuiteResponse } from "@/services/api_security_validation.service";

interface APIValidationRunButtonProps {
  onRunComplete: (result: APIValidationSuiteResponse) => void;
}

export const APIValidationRunButton: React.FC<APIValidationRunButtonProps> = ({
  onRunComplete,
}) => {
  const [running, setRunning] = useState(false);

  const handleRun = async () => {
    setRunning(true);
    try {
      const res = await APISecurityValidationService.runSuite();
      onRunComplete(res);
    } catch (err) {
      console.error("Failed to run API security validation suite:", err);
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
          <span>Evaluating API Assertions...</span>
        </>
      ) : (
        <>
          <Play className="h-4 w-4 fill-current" />
          <span>Run API Security Verification</span>
        </>
      )}
    </button>
  );
};
