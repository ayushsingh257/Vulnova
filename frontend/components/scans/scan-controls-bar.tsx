"use client";

import * as React from "react";
import { Pause, Play, XCircle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScansService } from "@/services/scans.service";

export function ScanControlsBar({
  scanId,
  status = "ASSESSING",
  onActionCompleted,
}: {
  scanId: string;
  status?: string;
  onActionCompleted?: () => void;
}) {
  const [loading, setLoading] = React.useState(false);

  const handlePause = async () => {
    setLoading(true);
    try {
      await ScansService.pauseScan(scanId);
      if (onActionCompleted) onActionCompleted();
    } finally {
      setLoading(false);
    }
  };

  const handleResume = async () => {
    setLoading(true);
    try {
      await ScansService.resumeScan(scanId);
      if (onActionCompleted) onActionCompleted();
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async () => {
    setLoading(true);
    try {
      await ScansService.cancelScan(scanId);
      if (onActionCompleted) onActionCompleted();
    } finally {
      setLoading(false);
    }
  };

  const handleRetry = async () => {
    setLoading(true);
    try {
      await ScansService.retryScan(scanId);
      if (onActionCompleted) onActionCompleted();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center space-x-3">
      {status === "PAUSED" ? (
        <Button variant="outline" size="sm" onClick={handleResume} disabled={loading}>
          <Play className="mr-1.5 h-3.5 w-3.5 text-emerald-400" />
          <span>Resume Scan</span>
        </Button>
      ) : (
        <Button variant="outline" size="sm" onClick={handlePause} disabled={loading || status === "COMPLETED"}>
          <Pause className="mr-1.5 h-3.5 w-3.5 text-amber-400" />
          <span>Pause Scan</span>
        </Button>
      )}

      <Button variant="outline" size="sm" onClick={handleCancel} disabled={loading || status === "COMPLETED"}>
        <XCircle className="mr-1.5 h-3.5 w-3.5 text-red-400" />
        <span>Cancel Scan</span>
      </Button>

      <Button variant="outline" size="sm" onClick={handleRetry} disabled={loading}>
        <RotateCcw className="mr-1.5 h-3.5 w-3.5 text-blue-400" />
        <span>Retry Scan</span>
      </Button>
    </div>
  );
}
