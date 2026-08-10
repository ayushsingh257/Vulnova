"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Terminal, ShieldCheck } from "lucide-react";
import { CLIIntegrationCard } from "@/components/integrations/ci-cd/CLIIntegrationCard";
import { TokenManagementPanel } from "@/components/integrations/ci-cd/TokenManagementPanel";
import { PipelineExampleViewer } from "@/components/integrations/ci-cd/PipelineExampleViewer";
import { ScanGateConfiguration } from "@/components/integrations/ci-cd/ScanGateConfiguration";

export default function CICDIntegrationPage() {
  const router = useRouter();

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-zinc-800 pb-6">
        <div className="flex items-center space-x-3">
          <button
            onClick={() => router.push("/integrations")}
            className="p-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
          </button>
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-600/20 border border-purple-500/40 text-purple-400 shadow-md">
            <Terminal className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-black tracking-tight text-white">
              CI/CD Pipeline Security Scanning
            </h1>
            <p className="text-xs text-zinc-400 mt-0.5">
              Integrate Vulnova security gates into GitHub Actions, GitLab CI/CD, and Jenkins pipelines
            </p>
          </div>
        </div>
      </div>

      {/* Top Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <CLIIntegrationCard />
        <TokenManagementPanel />
      </div>

      {/* Bottom Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <PipelineExampleViewer />
        <ScanGateConfiguration />
      </div>
    </div>
  );
}
