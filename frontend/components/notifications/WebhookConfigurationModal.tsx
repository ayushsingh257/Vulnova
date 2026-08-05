"use client";

import React, { useState } from "react";
import { X, Server, MessageSquare, ShieldAlert, Loader2 } from "lucide-react";
import {
  CreateChannelRequest,
  NotificationChannelDTO,
  NotificationsService,
} from "@/services/notifications.service";

interface WebhookConfigurationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  initialData?: NotificationChannelDTO | null;
}

export const WebhookConfigurationModal: React.FC<WebhookConfigurationModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  initialData,
}) => {
  const [provider, setProvider] = useState<"slack" | "teams">(
    (initialData?.provider as "slack" | "teams") || "slack"
  );
  const [name, setName] = useState(initialData?.name || "");
  const [webhookUrl, setWebhookUrl] = useState("");
  const [minSeverity, setMinSeverity] = useState(initialData?.min_severity || "HIGH");
  const [selectedEvents, setSelectedEvents] = useState<string[]>(
    initialData?.event_types || [
      "CRITICAL_FINDING_DISCOVERED",
      "HIGH_FINDING_DISCOVERED",
      "SCAN_COMPLETED",
      "SCAN_FAILED",
      "COMPLIANCE_SCORE_DROPPED",
    ]
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const AVAILABLE_EVENTS = [
    { id: "CRITICAL_FINDING_DISCOVERED", label: "Critical Severity Finding Discovered" },
    { id: "HIGH_FINDING_DISCOVERED", label: "High Severity Finding Discovered" },
    { id: "SCAN_STARTED", label: "Scan Execution Started" },
    { id: "SCAN_COMPLETED", label: "Scan Execution Completed" },
    { id: "SCAN_FAILED", label: "Scan Execution Failed" },
    { id: "COMPLIANCE_SCORE_DROPPED", label: "Compliance Score Drop Alert" },
    { id: "TICKET_CREATED", label: "Jira / GitHub Ticket Created" },
  ];

  const toggleEvent = (eventId: string) => {
    if (selectedEvents.includes(eventId)) {
      setSelectedEvents(selectedEvents.filter((e) => e !== eventId));
    } else {
      setSelectedEvents([...selectedEvents, eventId]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);

    try {
      if (initialData) {
        await NotificationsService.updateChannel(initialData.id, {
          name,
          webhook_url: webhookUrl ? webhookUrl : undefined,
          event_types: selectedEvents,
          min_severity: minSeverity,
        });
      } else {
        const payload: CreateChannelRequest = {
          provider,
          name,
          webhook_url: webhookUrl,
          event_types: selectedEvents,
          min_severity: minSeverity,
        };
        await NotificationsService.createChannel(payload);
      }
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to save webhook configuration");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg bg-zinc-950 border border-zinc-800 rounded-xl p-6 space-y-4 shadow-2xl">
        <div className="flex justify-between items-center border-b border-zinc-800 pb-3">
          <div>
            <h3 className="text-base font-bold text-white">
              {initialData ? "Edit Webhook Channel" : "Configure Webhook Channel"}
            </h3>
            <p className="text-xs text-zinc-400 mt-0.5">
              Connect Slack workspace or Microsoft Teams channel
            </p>
          </div>
          <button onClick={onClose} className="text-zinc-400 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 text-xs">
          {!initialData && (
            <div>
              <label className="block text-zinc-400 mb-1.5 font-medium">Webhook Destination Provider</label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setProvider("slack")}
                  className={`flex items-center justify-center space-x-2 p-3 rounded-lg border font-semibold transition-all ${
                    provider === "slack"
                      ? "border-blue-500 bg-blue-950/40 text-blue-400 shadow-md"
                      : "border-zinc-800 bg-zinc-900 text-zinc-400 hover:border-zinc-700"
                  }`}
                >
                  <Server className="h-4 w-4" />
                  <span>Slack Workspace</span>
                </button>
                <button
                  type="button"
                  onClick={() => setProvider("teams")}
                  className={`flex items-center justify-center space-x-2 p-3 rounded-lg border font-semibold transition-all ${
                    provider === "teams"
                      ? "border-purple-500 bg-purple-950/40 text-purple-400 shadow-md"
                      : "border-zinc-800 bg-zinc-900 text-zinc-400 hover:border-zinc-700"
                  }`}
                >
                  <MessageSquare className="h-4 w-4" />
                  <span>MS Teams Channel</span>
                </button>
              </div>
            </div>
          )}

          <div>
            <label className="block text-zinc-400 mb-1 font-medium">Channel Name</label>
            <input
              type="text"
              required
              placeholder={provider === "slack" ? "#sec-alerts" : "Security Response Team"}
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-md border border-zinc-800 bg-zinc-900 p-2.5 text-zinc-200"
            />
          </div>

          <div>
            <label className="block text-zinc-400 mb-1 font-medium">
              Incoming Webhook URL (AES-256 Encrypted)
            </label>
            <input
              type="password"
              required={!initialData}
              placeholder={
                initialData
                  ? "Leave blank to keep existing encrypted webhook URL"
                  : provider === "slack"
                  ? "https://hooks.slack.com/services/T.../B.../..."
                  : "https://outlook.office.com/webhook/..."
              }
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
              className="w-full rounded-md border border-zinc-800 bg-zinc-900 p-2.5 text-zinc-200"
            />
          </div>

          <div>
            <label className="block text-zinc-400 mb-1 font-medium">Minimum Severity Filter</label>
            <select
              value={minSeverity}
              onChange={(e) => setMinSeverity(e.target.value)}
              className="w-full rounded-md border border-zinc-800 bg-zinc-900 p-2.5 text-zinc-200 font-mono"
            >
              <option value="CRITICAL">CRITICAL Only</option>
              <option value="HIGH">HIGH & Above</option>
              <option value="MEDIUM">MEDIUM & Above</option>
              <option value="ALL">ALL Events (Including INFO/Scan Alerts)</option>
            </select>
          </div>

          <div>
            <label className="block text-zinc-400 mb-1.5 font-medium">Subscribed Event Types</label>
            <div className="space-y-2 max-h-36 overflow-y-auto pr-1">
              {AVAILABLE_EVENTS.map((ev) => (
                <label
                  key={ev.id}
                  className="flex items-center space-x-2 p-1.5 rounded-md hover:bg-zinc-900 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={selectedEvents.includes(ev.id)}
                    onChange={() => toggleEvent(ev.id)}
                    className="rounded border-zinc-700 bg-zinc-950 text-purple-600 focus:ring-purple-500"
                  />
                  <span className="text-zinc-300">{ev.label}</span>
                </label>
              ))}
            </div>
          </div>

          {error && <p className="text-red-400 text-[11px]">{error}</p>}

          <div className="flex justify-end space-x-2 pt-2 border-t border-zinc-800">
            <button
              type="button"
              onClick={onClose}
              className="px-3.5 py-2 rounded-md bg-zinc-800 text-zinc-300 font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex items-center space-x-2 px-4 py-2 rounded-md bg-purple-600 text-white font-semibold hover:bg-purple-500 transition-colors"
            >
              {saving ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin text-white" />
                  <span>Saving Webhook...</span>
                </>
              ) : (
                <span>Save Channel Configuration</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
