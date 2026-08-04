"use client";

import * as React from "react";
import { Terminal, Radio } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export function LiveEventConsole({
  logs = [
    "[10:01:12] [SYSTEM] Scan execution dispatched. Task assigned to Celery queue 'scans.default'.",
    "[10:02:45] [PROBE] Scope availability probe: DNS resolved 192.168.1.50 (200 OK).",
    "[10:04:30] [CRAWLER] Discovered 42 REST API endpoints. Parameters extracted.",
    "[10:08:15] [PLUGIN] Executing Active DAST Plugin: SqlInjectionPayloadProbe.",
    "[10:12:00] [FINDING] Discovered Vulnerability: High Severity Blind SQL Injection.",
  ],
}: {
  logs?: string[];
}) {
  return (
    <Card className="border-zinc-800 bg-zinc-950/80">
      <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-zinc-800/80">
        <div className="flex items-center space-x-2">
          <Terminal className="h-5 w-5 text-emerald-400" />
          <CardTitle className="text-sm font-bold font-mono">Live Streaming Event Log Console</CardTitle>
        </div>
        <div className="flex items-center space-x-2 text-xs font-mono text-emerald-400">
          <Radio className="h-3.5 w-3.5 animate-ping" />
          <span>WebSocket Stream Connected</span>
        </div>
      </CardHeader>

      <CardContent className="pt-4">
        <div className="h-48 overflow-y-auto font-mono text-xs p-3 rounded-xl border border-zinc-800/90 bg-zinc-950 text-zinc-300 space-y-1.5 selection:bg-emerald-500/30">
          {logs.map((log, idx) => (
            <div key={idx} className="leading-relaxed">
              <span className="text-emerald-400">{log.slice(0, 10)}</span>
              <span className="text-zinc-300">{log.slice(10)}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
