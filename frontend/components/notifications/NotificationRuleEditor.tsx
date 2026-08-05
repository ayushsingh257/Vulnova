"use client";

import React, { useEffect, useState } from "react";
import { ShieldCheck, Filter, BellRing, Check } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  NotificationRuleDTO,
  NotificationsService,
} from "@/services/notifications.service";

export const NotificationRuleEditor: React.FC = () => {
  const [rules, setRules] = useState<NotificationRuleDTO[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    NotificationsService.getRules()
      .then((data) => setRules(data))
      .catch((err) => console.error("Failed to load notification rules:", err))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return null;

  return (
    <Card className="border-zinc-800 bg-zinc-950/80 backdrop-blur-md">
      <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-zinc-800">
        <div className="flex items-center space-x-2">
          <Filter className="h-4 w-4 text-purple-400" />
          <CardTitle className="text-sm font-bold text-white">Event Routing & Severity Rules</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="pt-4 space-y-3">
        {rules.map((rule) => (
          <div
            key={rule.id}
            className="flex items-center justify-between p-3 rounded-lg border border-zinc-800 bg-zinc-900/60 text-xs"
          >
            <div className="space-y-1">
              <div className="font-semibold text-zinc-200 flex items-center space-x-2">
                <BellRing className="h-3.5 w-3.5 text-purple-400" />
                <span>{rule.name}</span>
              </div>
              <div className="flex flex-wrap gap-1 pt-0.5">
                {rule.event_types.map((ev) => (
                  <span
                    key={ev}
                    className="px-1.5 py-0.5 rounded bg-zinc-950 border border-zinc-800 text-[10px] font-mono text-zinc-400"
                  >
                    {ev}
                  </span>
                ))}
              </div>
            </div>
            <div className="flex items-center space-x-2 shrink-0">
              <Badge variant="info" className="text-xs font-mono font-bold">
                Min: {rule.min_severity}
              </Badge>
              <Badge variant="success" className="text-[10px]">
                ENABLED
              </Badge>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
};
