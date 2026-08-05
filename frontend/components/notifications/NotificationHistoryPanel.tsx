"use client";

import React from "react";
import { Activity, CheckCircle2, AlertTriangle, ShieldAlert } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export const NotificationHistoryPanel: React.FC = () => {
  return (
    <Card className="border-zinc-800 bg-zinc-950/80 backdrop-blur-md">
      <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-zinc-800">
        <div className="flex items-center space-x-2">
          <Activity className="h-4 w-4 text-purple-400" />
          <CardTitle className="text-sm font-bold text-white">Recent Notification Deliveries</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="pt-4">
        <div className="space-y-2 text-xs">
          <div className="flex items-center justify-between p-3 rounded-lg border border-zinc-800 bg-zinc-900/60">
            <div className="flex items-center space-x-3">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <div>
                <span className="font-semibold text-zinc-200 block">CRITICAL_FINDING_DISCOVERED</span>
                <span className="text-[11px] text-zinc-400">Slack #sec-alerts | HTTP 200 OK</span>
              </div>
            </div>
            <span className="text-[11px] text-zinc-500 font-mono">Just now</span>
          </div>

          <div className="flex items-center justify-between p-3 rounded-lg border border-zinc-800 bg-zinc-900/60">
            <div className="flex items-center space-x-3">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <div>
                <span className="font-semibold text-zinc-200 block">SCAN_COMPLETED</span>
                <span className="text-[11px] text-zinc-400">MS Teams Security Channel | HTTP 200 OK</span>
              </div>
            </div>
            <span className="text-[11px] text-zinc-500 font-mono">5 mins ago</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
