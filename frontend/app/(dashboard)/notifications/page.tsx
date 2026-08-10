"use client";

import React, { useEffect, useState } from "react";
import { Loader2, Bell, Plus } from "lucide-react";
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
  const [showModal, setShowModal] = useState(false);
  const [editChannel, setEditChannel] = useState<NotificationChannelDTO | undefined>();

  const fetchChannels = async () => {
    setLoading(true);
    try {
      const data = await NotificationsService.getChannels();
      setChannels(data);
    } catch (err) {
      console.error("Failed to fetch notification channels:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchChannels();
  }, []);

  const handleAddChannel = () => {
    setEditChannel(undefined);
    setShowModal(true);
  };

  const handleEditChannel = (channel: NotificationChannelDTO) => {
    setEditChannel(channel);
    setShowModal(true);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-zinc-800 pb-6">
        <div className="flex items-center space-x-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-600/20 border border-purple-500/40 text-purple-400 shadow-md">
            <Bell className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tight text-white">
              Enterprise Notification Channels & Webhook Alerts
            </h1>
            <p className="text-xs text-zinc-400 mt-0.5">
              Multi-channel security alert dispatching across Slack, Microsoft Teams, PagerDuty, Email, and Custom Webhooks
            </p>
          </div>
        </div>

        <button
          onClick={handleAddChannel}
          className="px-4 py-2 rounded-lg bg-purple-600 font-bold text-xs text-white hover:bg-purple-500 transition-colors flex items-center space-x-2 shadow-md"
        >
          <Plus className="h-4 w-4" />
          <span>Add Notification Channel</span>
        </button>
      </div>

      {loading ? (
        <div className="text-center py-16 text-zinc-500 text-sm flex items-center justify-center space-x-2">
          <Loader2 className="h-5 w-5 animate-spin text-purple-500" />
          <span>Loading active notification channels...</span>
        </div>
      ) : (
        <>
          {/* Channel Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {channels.map((channel) => (
              <NotificationChannelCard
                key={channel.id}
                channel={channel}
                onEdit={() => handleEditChannel(channel)}
                onRefresh={fetchChannels}
              />
            ))}
          </div>

          {/* Rule Editor */}
          <NotificationRuleEditor />

          {/* Alert History Log Panel */}
          <NotificationHistoryPanel />
        </>
      )}

      <WebhookConfigurationModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        onSuccess={fetchChannels}
        initialData={editChannel}
      />
    </div>
  );
}
