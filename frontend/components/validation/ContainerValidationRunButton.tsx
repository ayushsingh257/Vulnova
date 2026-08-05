"use client";

import React, { useState } from "react";
import { Play, Loader2 } from "lucide-react";
import { ContainerValidationService, ContainerValidationSuiteResponse } from "@/services/container_validation.service";

interface ContainerValidationRunButtonProps {
  onRunComplete: (result: ContainerValidationSuiteResponse) => void;
}

export const ContainerValidationRunButton: React.FC<ContainerValidationRunButtonProps> = ({
  onRunComplete,
}) => {
  const [running, setRunning] = useState(false);

  const handleRun = async () => {
    setRunning(true);
    try {
      const res = await ContainerValidationService.runSuite();
      onRunComplete(res);
    } catch (err) {
      console.error("Failed to run container validation suite:", err);
    } finally {
      setRunning(false);
    }
  };

  return (
    <button
      onClick={handleRun}
      disabled={running}
      className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-cyan-600 font-bold text-xs text-white hover:bg-cyan-500 transition-colors disabled:opacity-50"
    >
      {running ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Evaluating Container Security...</span>
        </>
      ) : (
        <>
          <Play className="h-4 w-4 fill-current" />
          <span>Run Container Audit</span>
        </>
      )}
    </button>
  );
};
