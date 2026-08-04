"use client";

import * as React from "react";
import { Layers, ArrowUpRight, ShieldAlert, Globe } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export interface TopVulnerableAsset {
  target_id: string;
  target_url: string;
  environment: string;
  risk_score: number;
  critical_count: number;
  high_count: number;
}

export function AssetRiskOverview({ assets }: { assets: TopVulnerableAsset[] }) {
  const getEnvBadge = (env: string) => {
    switch (env.toUpperCase()) {
      case "PRODUCTION":
        return <Badge variant="critical">PRODUCTION</Badge>;
      case "STAGING":
        return <Badge variant="warning">STAGING</Badge>;
      default:
        return <Badge variant="default">{env.toUpperCase()}</Badge>;
    }
  };

  return (
    <Card className="border-zinc-800 bg-zinc-950/80">
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <div className="flex items-center space-x-2">
          <Layers className="h-5 w-5 text-red-500" />
          <CardTitle className="text-lg font-bold">Top High-Risk Target Assets</CardTitle>
        </div>
        <span className="text-xs text-zinc-400 font-mono">
          Crown Jewel Assets
        </span>
      </CardHeader>

      <CardContent className="space-y-3">
        {assets.length === 0 ? (
          <div className="p-6 text-center text-xs text-zinc-500 border border-dashed border-zinc-800 rounded-lg">
            No active target assets registered.
          </div>
        ) : (
          assets.map((asset) => (
            <div
              key={asset.target_id}
              className="flex items-center justify-between p-3.5 rounded-lg border border-zinc-800/60 bg-zinc-900/30 hover:border-zinc-700 transition-all"
            >
              <div className="flex items-center space-x-3">
                <div className="p-2 rounded-md bg-zinc-800/80 text-zinc-300">
                  <Globe className="h-4 w-4" />
                </div>
                <div>
                  <div className="text-xs font-bold text-zinc-100 flex items-center space-x-2">
                    <span>{asset.target_url}</span>
                    <ArrowUpRight className="h-3 w-3 text-zinc-500" />
                  </div>
                  <div className="flex items-center space-x-2 mt-1">
                    {getEnvBadge(asset.environment)}
                    <span className="text-[10px] text-zinc-400">
                      {asset.critical_count} Crit / {asset.high_count} High
                    </span>
                  </div>
                </div>
              </div>

              <div className="text-right">
                <div className="font-mono text-sm font-bold text-red-400">
                  {asset.risk_score.toFixed(1)}
                </div>
                <div className="text-[10px] uppercase text-zinc-500 tracking-wider">
                  Risk Score
                </div>
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
