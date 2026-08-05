"use client";

import React, { useState } from "react";
import { Play, Loader2 } from "lucide-react";
import { InfrastructureValidationService, InfrastructureValidationSuiteResponse } from "@/services/infrastructure_validation.service";

interface InfrastructureValidationRunButtonProps {
  onRunComplete: (result: InfrastructureValidationSuiteResponse) => void;
}

export const InfrastructureValidationRunButton: React.FC<InfrastructureValidationRunButtonProps> = ({
  onRunComplete,
}) => {
  const [running, setRunning] = useState(false);

  const handleRun = async () => {
    setRunning(true);
    try {
      const res = await InfrastructureValidationService.runSuite();
      onRunComplete(res);
    } catch (err) {
      console.error("Failed to run infrastructure validation suite:", err);
    } finally {
      setRunning(false);
    }
  };

  return (
    <button
      onClick={handleRun}
      disabled={running}
      className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-emerald-600 font-bold text-xs text-white hover:bg-emerald-500 transition-colors disabled:opacity-50"
    >
      {running ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Evaluating Infrastructure Assertions...</span>
        </>
      ) : (
        <>
          <Play className="h-4 w-4 fill-current" />
          <span>Run Infrastructure Verification</span>
        </>
      )}
    </button>
  );
};
