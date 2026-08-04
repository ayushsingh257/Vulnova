"use client";

import * as React from "react";
import { CheckCircle2, Clock, PlayCircle, AlertCircle } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export interface TimelineItem {
  timestamp: string;
  stage: string;
  title: string;
  description: string;
  status: string;
}

export function ScanActivityTimeline({
  items = [
    {
      timestamp: "10:01:12 UTC",
      stage: "QUEUED",
      title: "Job Dispatched & Priority Queued",
      description: "Scan task submitted to worker pool (scans.default) and verified against authorized CFAA contract.",
      status: "COMPLETED",
    },
    {
      timestamp: "10:02:45 UTC",
      stage: "PROBING",
      title: "Target Scope Verification",
      description: "DNS resolution, SSL handshake, and host availability probes completed successfully.",
      status: "COMPLETED",
    },
    {
      timestamp: "10:04:30 UTC",
      stage: "CRAWLING",
      title: "Attack Surface Crawling & Endpoint Mapping",
      description: "Discovered 42 unique REST API endpoints, form inputs, and dynamic DOM parameters.",
      status: "COMPLETED",
    },
    {
      timestamp: "10:08:15 UTC",
      stage: "ASSESSING",
      title: "Dynamic Plugin Assessment",
      description: "Executing active DAST plugin suites (SQLi, XSS, SSRF, RCE payload probes).",
      status: "IN_PROGRESS",
    },
  ],
}: {
  items?: TimelineItem[];
}) {
  const getStatusIcon = (status: string) => {
    switch (status.toUpperCase()) {
      case "COMPLETED":
        return <CheckCircle2 className="h-4 w-4 text-emerald-400" />;
      case "IN_PROGRESS":
        return <PlayCircle className="h-4 w-4 text-red-400 animate-pulse" />;
      case "FAILED":
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Clock className="h-4 w-4 text-zinc-500" />;
    }
  };

  return (
    <Card className="border-zinc-800 bg-zinc-950/80">
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <div className="flex items-center space-x-2">
          <Clock className="h-5 w-5 text-red-500" />
          <CardTitle className="text-lg font-bold">Scan Activity Execution Timeline</CardTitle>
        </div>
        <span className="text-xs text-zinc-400 font-mono">
          Milestones: <strong className="text-white">{items.length}</strong>
        </span>
      </CardHeader>

      <CardContent>
        <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-zinc-800">
          {items.map((item, idx) => (
            <div key={idx} className="relative space-y-1 group">
              <div className="absolute -left-[1.375rem] top-0.5 bg-zinc-950 p-0.5 rounded-full">
                {getStatusIcon(item.status)}
              </div>

              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-zinc-200">{item.title}</span>
                <div className="flex items-center space-x-2">
                  <Badge variant="info" className="font-mono text-[10px]">
                    {item.stage}
                  </Badge>
                  <span className="text-[10px] font-mono text-zinc-500">{item.timestamp}</span>
                </div>
              </div>

              <p className="text-xs text-zinc-400 leading-relaxed">{item.description}</p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
