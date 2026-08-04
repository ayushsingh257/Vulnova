"use client";

import * as React from "react";
import { ShieldAlert, AlertTriangle, Info, CheckCircle2 } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export interface ThreatAlert {
  severity: string;
  category: string;
  title: string;
  description: string;
  affected_target_url?: string;
}

export function ThreatAdvisoriesDrawer({
  advisories = [
    {
      severity: "CRITICAL",
      category: "VULNERABILITY_CVSS_CRITICAL",
      title: "Critical Finding: Unauthenticated RCE Detected",
      description: "Critical vulnerability identified in target scope. Immediate patch remediation required.",
      affected_target_url: "https://api.staging.vulnova.internal",
    },
    {
      severity: "WARNING",
      category: "REMEDIATION_SLA_BREACH",
      title: "Remediation SLA Breach Warning",
      description: "Critical finding unmitigated for >14 days. SLA threshold exceeded.",
    },
    {
      severity: "INFO",
      category: "AUTHORIZED_CONTRACT_STATUS",
      title: "Authorized Scope Contract Active",
      description: "Authorized assessment contract active under CFAA governance rules.",
    },
  ],
}: {
  advisories?: ThreatAlert[];
}) {
  const getSeverityBadge = (severity: string) => {
    switch (severity.toUpperCase()) {
      case "CRITICAL":
        return (
          <Badge variant="critical" className="font-mono text-[10px] space-x-1">
            <AlertTriangle className="h-3 w-3 animate-pulse" />
            <span>CRITICAL ADVISORY</span>
          </Badge>
        );
      case "WARNING":
        return (
          <Badge variant="warning" className="font-mono text-[10px] space-x-1">
            <AlertTriangle className="h-3 w-3" />
            <span>SLA WARNING</span>
          </Badge>
        );
      default:
        return (
          <Badge variant="info" className="font-mono text-[10px] space-x-1">
            <Info className="h-3 w-3" />
            <span>GOVERNANCE INFO</span>
          </Badge>
        );
    }
  };

  return (
    <Card className="border-zinc-800 bg-zinc-950/80">
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <div className="flex items-center space-x-2">
          <ShieldAlert className="h-5 w-5 text-red-500" />
          <CardTitle className="text-lg font-bold">Executive Threat Advisories & SLA Alerts</CardTitle>
        </div>
        <span className="text-xs text-zinc-400 font-mono">
          Active Alerts: <strong className="text-red-400">{advisories.length}</strong>
        </span>
      </CardHeader>

      <CardContent>
        <div className="space-y-3">
          {advisories.map((alert, idx) => (
            <div
              key={idx}
              className="p-3.5 rounded-xl border border-zinc-800/80 bg-zinc-900/40 space-y-1.5 hover:border-zinc-700 transition-all"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-zinc-200">{alert.title}</span>
                {getSeverityBadge(alert.severity)}
              </div>
              <p className="text-xs text-zinc-400 leading-relaxed">{alert.description}</p>
              {alert.affected_target_url && (
                <div className="text-[10px] font-mono text-zinc-500 pt-1">
                  Target Scope: <span className="text-zinc-300">{alert.affected_target_url}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
