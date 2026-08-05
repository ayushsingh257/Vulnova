"use client";

import React, { useState } from "react";
import { Terminal, Copy, Check, ShieldCheck, Download, Code } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export const CLIIntegrationCard: React.FC = () => {
  const [copied, setCopied] = useState(false);

  const installCmd = "pip install vulnova-cli";

  const handleCopy = () => {
    navigator.clipboard.writeText(installCmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Card className="border-zinc-800 bg-zinc-950/80 backdrop-blur-md">
      <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-zinc-800">
        <div className="flex items-center space-x-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-600/20 border border-purple-500/40 text-purple-400">
            <Terminal className="h-5 w-5" />
          </div>
          <div>
            <CardTitle className="text-base font-bold text-white">
              Vulnova Developer CLI Tool
            </CardTitle>
            <p className="text-xs text-zinc-400 mt-0.5">
              Distributable Python CLI for local workstations and CI/CD pipelines
            </p>
          </div>
        </div>

        <Badge variant="info" className="text-xs font-mono font-bold">
          v0.1.0 STABLE
        </Badge>
      </CardHeader>

      <CardContent className="pt-4 space-y-4 text-xs">
        <div>
          <span className="text-zinc-400 font-medium block mb-1.5">
            1. Install CLI Package via PyPI / Pip:
          </span>
          <div className="flex items-center justify-between bg-zinc-900 border border-zinc-800 rounded-lg p-3 font-mono text-zinc-200">
            <code>{installCmd}</code>
            <button
              onClick={handleCopy}
              className="text-zinc-400 hover:text-white p-1 rounded transition-colors"
              title="Copy Command"
            >
              {copied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
            </button>
          </div>
        </div>

        <div>
          <span className="text-zinc-400 font-medium block mb-1.5">
            2. Authenticate CLI session:
          </span>
          <pre className="bg-zinc-900 border border-zinc-800 rounded-lg p-3 font-mono text-zinc-300 text-[11px] overflow-x-auto">
            vulnova auth login --token vn_cli_xxxxxxxxxxxx --server https://api.vulnova.com
          </pre>
        </div>

        <div className="flex items-center space-x-4 pt-2 text-zinc-400 text-[11px]">
          <span className="flex items-center space-x-1">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
            <span>Zero DB Dependency</span>
          </span>
          <span className="flex items-center space-x-1">
            <Code className="h-3.5 w-3.5 text-purple-400" />
            <span>--json & --quiet Ready</span>
          </span>
        </div>
      </CardContent>
    </Card>
  );
};
