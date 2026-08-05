"use client";

import React, { useState } from "react";
import { Send, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import {
  NotificationDeliveryResponse,
  NotificationsService,
} from "@/services/notifications.service";

interface TestNotificationButtonProps {
  channelId: string;
  channelName: string;
  onDelivered?: (res: NotificationDeliveryResponse) => void;
}

export const TestNotificationButton: React.FC<TestNotificationButtonProps> = ({
  channelId,
  channelName,
  onDelivered,
}) => {
  const [testing, setTesting] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  const handleTest = async () => {
    setTesting(true);
    setStatus(null);
    try {
      const res = await NotificationsService.sendTestNotification(channelId);
      if (res.status === "DELIVERED") {
        setStatus("SUCCESS");
      } else {
        setStatus(`FAILED: ${res.error_message || "HTTP delivery failed"}`);
      }
      if (onDelivered) onDelivered(res);
    } catch (err: any) {
      setStatus(`FAILED: ${err.message || "Failed to send test alert"}`);
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="flex items-center space-x-2">
      <button
        onClick={handleTest}
        disabled={testing}
        className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-zinc-800 border border-zinc-700 text-xs font-semibold text-zinc-200 hover:bg-zinc-700 hover:text-white transition-colors"
      >
        {testing ? (
          <>
            <Loader2 className="h-3.5 w-3.5 animate-spin text-purple-400" />
            <span>Sending Test...</span>
          </>
        ) : (
          <>
            <Send className="h-3.5 w-3.5 text-purple-400" />
            <span>Send Test Alert</span>
          </>
        )}
      </button>

      {status === "SUCCESS" && (
        <span className="flex items-center space-x-1 text-[11px] font-bold text-emerald-400">
          <CheckCircle2 className="h-3.5 w-3.5" />
          <span>Delivered!</span>
        </span>
      )}
      {status && status.startsWith("FAILED") && (
        <span className="flex items-center space-x-1 text-[11px] font-bold text-red-400 truncate max-w-[200px]" title={status}>
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          <span className="truncate">{status}</span>
        </span>
      )}
    </div>
  );
};
