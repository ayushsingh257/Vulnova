"use client";

import * as React from "react";
import { Calendar, Clock, Play, CheckCircle } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export interface SchedulesOverviewSummary {
  total_active_schedules: number;
  next_scheduled_run_at?: string | null;
}

export function SchedulesOverview({ summary }: { summary: SchedulesOverviewSummary }) {
  return (
    <Card className="border-zinc-800 bg-zinc-950/80">
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <div className="flex items-center space-x-2">
          <Calendar className="h-5 w-5 text-red-500" />
          <CardTitle className="text-lg font-bold">Recurring Scan Schedules</CardTitle>
        </div>
        <span className="text-xs text-zinc-400 font-mono">
          Celery Beat Orchestrator
        </span>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="p-3.5 rounded-lg border border-zinc-800/80 bg-zinc-900/40">
            <div className="text-xs text-zinc-400">Active Schedules</div>
            <div className="text-2xl font-bold text-zinc-100 mt-1">
              {summary.total_active_schedules}
            </div>
          </div>

          <div className="p-3.5 rounded-lg border border-zinc-800/80 bg-zinc-900/40">
            <div className="text-xs text-zinc-400">Next Scheduled Run</div>
            <div className="text-xs font-mono font-semibold text-emerald-400 mt-1 truncate">
              {summary.next_scheduled_run_at
                ? new Date(summary.next_scheduled_run_at).toLocaleString()
                : "No active runs due"}
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-zinc-800/60">
          <span className="text-xs text-zinc-400 flex items-center space-x-1.5">
            <Clock className="h-3.5 w-3.5 text-zinc-500" />
            <span>Automated Cron Engine</span>
          </span>
          <Button variant="outline" size="sm">
            <Play className="h-3.5 w-3.5 mr-1.5 text-red-400" />
            Trigger Tick
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
