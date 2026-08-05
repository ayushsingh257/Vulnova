"use client";

import React, { useEffect, useState } from "react";
import { Loader2, Bell, Plus, Settings, Server, MessageSquare } from "lucide-react";
import { DashboardLayout } from "@/components/dashboard/dashboard-layout";
import {
  NotificationChannelDTO,
  NotificationsService,
} from "@/services/notifications.service";
import { NotificationChannelCard } from "@/components/notifications/NotificationChannelCard";
import { WebhookConfigurationModal } from "@/components/notifications/WebhookConfigurationModal";
import { NotificationRuleEditor } from "@/components/notifications/NotificationRuleEditor";
import { NotificationHistoryPanel } from "@/components/notifications/NotificationHistoryPanel";

export default function NotificationsDashboardPage() {
  const [channels, setChannels] = useState<NotificationChannelDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showModal, setShowModal] = useState(false);
  const [editChannel, setEditChannel] = useState<NotificationChannelDTO | null>(null);

  const fetchChannels = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await NotificationsService.getChannels();
      setChannels(data);
    } catch (err: any) {
      console.error("Failed to fetch notification channels:", err);
      setError(err.message || "Failed to load notification channels");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchChannels();
  }, []);

  const handleOpenCreate = () => {
    setEditChannel(null);
    setShowModal(true);
  };

  const handleEdit = (ch: NotificationChannelDTO) => {
    setEditChannel(ch);
    setShowModal(true);
  };

  return (
    <DashboardLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-zinc-800 pb-6">
          <div className="flex items-center space-x-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-600/20 border border-purple-500/40 text-purple-400 shadow-md">
              <Bell className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-black tracking-tight text-white">
                Real-Time Security Notification Center
              </h1>
              <p className="text-xs text-zinc-400 mt-0.5">
                Instant alert webhooks for Slack Workspaces and Microsoft Teams Channels
              </p>
            </div>
          </div>

          <button
            onClick={handleOpenCreate}
            className="flex items-center space-x-2 rounded-xl bg-purple-600 px-4 py-2 text-xs font-semibold text-white hover:bg-purple-500 transition-colors shadow-lg shadow-purple-950/40"
          >
            <Plus className="h-4 w-4" />
            <span>Add Webhook Channel</span>
          </button>
        </div>

        {loading ? (
          <div className="p-12 text-center text-zinc-400">
            <Loader2 className="w-8 h-8 animate-spin text-purple-400 mx-auto mb-3" />
            <p className="text-sm font-semibold text-zinc-300">
              Loading notification channels...
            </p>
          </div>
        ) : error ? (
          <div className="rounded-xl border border-red-900/60 bg-red-950/20 p-6 text-center text-red-400 text-xs font-semibold">
            {error}
          </div>
        ) : (
          <div className="space-y-8">
            {channels.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-zinc-800 bg-zinc-950/60 p-12 text-center space-y-4">
                <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-zinc-900 border border-zinc-800 text-purple-400">
                  <Bell className="h-7 w-7" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">No Notification Channels Configured</h3>
                  <p className="text-xs text-zinc-400 max-w-md mx-auto mt-1">
                    Connect your Slack workspace or Microsoft Teams channel to receive real-time critical vulnerability and scan execution alerts.
                  </p>
                </div>
                <button
                  onClick={handleOpenCreate}
                  className="inline-flex items-center space-x-2 rounded-xl bg-purple-600 px-4 py-2 text-xs font-semibold text-white hover:bg-purple-500 transition-colors"
                >
                  <Plus className="h-4 w-4" />
                  <span>Configure First Webhook Channel</span>
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {channels.map((ch) => (
                  <NotificationChannelCard
                    key={ch.id}
                    channel={ch}
                    onRefresh={fetchChannels}
                    onEdit={handleEdit}
                  />
                ))}
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <NotificationRuleEditor />
              <NotificationHistoryPanel />
            </div>
          </div>
        )}

        <WebhookConfigurationModal
          isOpen={showModal}
          onClose={() => setShowModal(false)}
          onSuccess={fetchChannels}
          initialData={editChannel}
        />
      </div>
    </DashboardLayout>
  );
}
