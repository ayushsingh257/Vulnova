"use client";

import React, { useState } from "react";
import { Server, MessageSquare, Trash2, Edit3, ShieldAlert } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  NotificationChannelDTO,
  NotificationsService,
} from "@/services/notifications.service";
import { TestNotificationButton } from "./TestNotificationButton";

interface NotificationChannelCardProps {
  channel: NotificationChannelDTO;
  onRefresh: () => void;
  onEdit: (channel: NotificationChannelDTO) => void;
}

export const NotificationChannelCard: React.FC<NotificationChannelCardProps> = ({
  channel,
  onRefresh,
  onEdit,
}) => {
  const [deleting, setDeleting] = useState(false);
  const [toggling, setToggling] = useState(false);

  const handleDelete = async () => {
    if (!confirm(`Are you sure you want to delete channel "${channel.name}"?`)) return;
    setDeleting(true);
    try {
      await NotificationsService.deleteChannel(channel.id);
      onRefresh();
    } catch (err) {
      console.error("Failed to delete channel:", err);
    } finally {
      setDeleting(false);
    }
  };

  const handleToggleActive = async () => {
    setToggling(true);
    try {
      await NotificationsService.updateChannel(channel.id, {
        is_active: !channel.is_active,
      });
      onRefresh();
    } catch (err) {
      console.error("Failed to toggle channel status:", err);
    } finally {
      setToggling(false);
    }
  };

  const isSlack = channel.provider === "slack";

  return (
    <Card className="border-zinc-800 bg-zinc-950/80 backdrop-blur-md">
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <div className="flex items-center space-x-3">
          <div
            className={`flex h-10 w-10 items-center justify-center rounded-xl border ${
              isSlack
                ? "bg-blue-950/50 border-blue-800/60 text-blue-400"
                : "bg-purple-950/50 border-purple-800/60 text-purple-400"
            }`}
          >
            {isSlack ? <Server className="h-5 w-5" /> : <MessageSquare className="h-5 w-5" />}
          </div>
          <div>
            <CardTitle className="text-base font-bold text-white">{channel.name}</CardTitle>
            <p className="text-xs text-zinc-400 uppercase font-mono tracking-wider">
              {channel.provider} Webhook
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={handleToggleActive}
            disabled={toggling}
            className={`px-2.5 py-1 rounded-full text-[11px] font-bold border transition-colors ${
              channel.is_active
                ? "border-emerald-800/60 bg-emerald-950/40 text-emerald-400"
                : "border-zinc-800 bg-zinc-900 text-zinc-500"
            }`}
          >
            {channel.is_active ? "ACTIVE" : "PAUSED"}
          </button>
        </div>
      </CardHeader>

      <CardContent className="pt-3 space-y-3">
        <div className="space-y-1.5 text-xs font-mono bg-zinc-900/60 p-3 rounded-lg border border-zinc-800">
          <div className="flex justify-between">
            <span className="text-zinc-500">Webhook URL:</span>
            <span className="text-zinc-300 font-semibold truncate max-w-[220px]">
              {channel.webhook_url_masked}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-zinc-500">Min Severity:</span>
            <Badge variant="info" className="text-xs font-bold font-mono">
              {channel.min_severity}
            </Badge>
          </div>
        </div>

        <div>
          <span className="text-[11px] text-zinc-500 font-medium block mb-1">Subscribed Events:</span>
          <div className="flex flex-wrap gap-1">
            {channel.event_types.map((ev) => (
              <span
                key={ev}
                className="px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-[10px] font-mono text-zinc-300"
              >
                {ev}
              </span>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-zinc-800">
          <TestNotificationButton channelId={channel.id} channelName={channel.name} />

          <div className="flex items-center space-x-1">
            <button
              onClick={() => onEdit(channel)}
              className="p-1.5 text-zinc-400 hover:text-white bg-zinc-900 border border-zinc-800 rounded-lg transition-colors"
              title="Edit Channel"
            >
              <Edit3 className="h-3.5 w-3.5" />
            </button>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="p-1.5 text-zinc-400 hover:text-red-400 bg-zinc-900 border border-zinc-800 rounded-lg transition-colors"
              title="Delete Channel"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
