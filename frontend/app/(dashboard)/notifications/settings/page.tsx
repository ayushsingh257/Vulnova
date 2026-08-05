"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, ArrowLeft, Plus } from "lucide-react";
import { DashboardLayout } from "@/components/dashboard/dashboard-layout";
import {
  NotificationChannelDTO,
  NotificationsService,
} from "@/services/notifications.service";
import { NotificationChannelCard } from "@/components/notifications/NotificationChannelCard";
import { WebhookConfigurationModal } from "@/components/notifications/WebhookConfigurationModal";

export default function NotificationSettingsPage() {
  const router = useRouter();
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
      console.error("Failed to fetch notification settings:", err);
      setError(err.message || "Failed to load notification settings");
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
        <div className="flex items-center justify-between border-b border-zinc-800 pb-4">
          <button
            onClick={() => router.push("/notifications")}
            className="flex items-center space-x-2 text-xs font-semibold text-zinc-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Back to Notification Center</span>
          </button>

          <button
            onClick={handleOpenCreate}
            className="flex items-center space-x-2 rounded-xl bg-purple-600 px-4 py-2 text-xs font-semibold text-white hover:bg-purple-500 transition-colors"
          >
            <Plus className="h-4 w-4" />
            <span>Add Webhook Channel</span>
          </button>
        </div>

        {loading ? (
          <div className="p-12 text-center text-zinc-400">
            <Loader2 className="w-8 h-8 animate-spin text-purple-400 mx-auto mb-3" />
            <p className="text-sm font-semibold text-zinc-300">
              Loading notification settings...
            </p>
          </div>
        ) : error ? (
          <div className="rounded-xl border border-red-900/60 bg-red-950/20 p-6 text-center text-red-400 text-xs font-semibold">
            {error}
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
