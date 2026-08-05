"use client";

import React, { useState } from "react";
import { Award, Loader2 } from "lucide-react";
import { CertificationValidationService, CertificationValidationSuiteResponse } from "@/services/certification_validation.service";

interface CertificationValidationRunButtonProps {
  onRunComplete: (result: CertificationValidationSuiteResponse) => void;
}

export const CertificationValidationRunButton: React.FC<CertificationValidationRunButtonProps> = ({
  onRunComplete,
}) => {
  const [running, setRunning] = useState(false);

  const handleRun = async () => {
    setRunning(true);
    try {
      const res = await CertificationValidationService.runSuite();
      onRunComplete(res);
    } catch (err) {
      console.error("Failed to run certification validation suite:", err);
    } finally {
      setRunning(false);
    }
  };

  return (
    <button
      onClick={handleRun}
      disabled={running}
      className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-amber-600 font-bold text-xs text-white hover:bg-amber-500 transition-colors disabled:opacity-50"
    >
      {running ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Evaluating Final Security Certification...</span>
        </>
      ) : (
        <>
          <Award className="h-4 w-4 fill-current" />
          <span>Run Final Certification</span>
        </>
      )}
    </button>
  );
};
