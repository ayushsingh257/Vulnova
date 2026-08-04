"use client";

import * as React from "react";
import { Lock, Cpu, Server, Key, Terminal } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export function EncryptionCard() {
  return (
    <Card className="border-zinc-800 bg-zinc-950/80">
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <div className="flex items-center space-x-2">
          <Lock className="h-5 w-5 text-red-500" />
          <CardTitle className="text-lg font-bold">Cryptographic & Container Sandbox Boundaries</CardTitle>
        </div>
        <span className="text-xs text-zinc-400 font-mono">
          Defense-in-Depth Architecture
        </span>
      </CardHeader>

      <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Encryption Controls */}
        <div className="p-4 rounded-xl border border-zinc-800/80 bg-zinc-900/40 space-y-4">
          <div className="text-sm font-bold text-zinc-200 flex items-center space-x-2">
            <Key className="h-4 w-4 text-amber-400" />
            <span>Cryptographic Standards</span>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-zinc-950/60 border border-zinc-800">
              <span className="text-zinc-400">Data-at-Rest Encryption</span>
              <span className="font-mono text-zinc-100 font-bold">AES-256-GCM Envelope</span>
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-lg bg-zinc-950/60 border border-zinc-800">
              <span className="text-zinc-400">Data-in-Transit Encryption</span>
              <span className="font-mono text-zinc-100 font-bold">TLS 1.3 / HSTS Preloaded</span>
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-lg bg-zinc-950/60 border border-zinc-800">
              <span className="text-zinc-400">Auth Token Signing</span>
              <span className="font-mono text-zinc-100 font-bold">RS256 / EdDSA JWTs</span>
            </div>
          </div>
        </div>

        {/* Container Sandbox Controls */}
        <div className="p-4 rounded-xl border border-zinc-800/80 bg-zinc-900/40 space-y-4">
          <div className="text-sm font-bold text-zinc-200 flex items-center space-x-2">
            <Terminal className="h-4 w-4 text-emerald-400" />
            <span>Container Sandbox Worker Isolation</span>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-zinc-950/60 border border-zinc-800">
              <span className="text-zinc-400">Execution User Privilege</span>
              <span className="font-mono text-emerald-400 font-bold">UID 10001 (Non-root)</span>
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-lg bg-zinc-950/60 border border-zinc-800">
              <span className="text-zinc-400">Container Filesystem</span>
              <span className="font-mono text-emerald-400 font-bold">read_only_rootfs: true</span>
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-lg bg-zinc-950/60 border border-zinc-800">
              <span className="text-zinc-400">Network & Egress Boundary</span>
              <span className="font-mono text-zinc-100 font-bold">Private Subnet Egress Proxy</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
