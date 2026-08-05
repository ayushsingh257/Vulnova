"use client";

import React, { useState } from "react";
import { Play, Loader2 } from "lucide-react";
import { RegressionValidationService, RegressionValidationSuiteResponse } from "@/services/regression_validation.service";

interface RegressionValidationRunButtonProps {
  onRunComplete: (result: RegressionValidationSuiteResponse) => void;
}

export const RegressionValidationRunButton: React.FC<RegressionValidationRunButtonProps> = ({
  onRunComplete,
}) => {
  const [running, setRunning] = useState(false);

  const handleRun = async () => {
    setRunning(true);
    try {
      const res = await RegressionValidationService.runSuite();
      onRunComplete(res);
    } catch (err) {
      console.error("Failed to run regression validation suite:", err);
    } finally {
      setRunning(false);
    }
  };

  return (
    <button
      onClick={handleRun}
      disabled={running}
      className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-teal-600 font-bold text-xs text-white hover:bg-teal-500 transition-colors disabled:opacity-50"
    >
      {running ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Evaluating Security Regressions...</span>
        </>
      ) : (
        <>
          <Play className="h-4 w-4 fill-current" />
          <span>Run Regression Test</span>
        </>
      )}
    </button>
  );
};
