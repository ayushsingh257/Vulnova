import * as React from "react";
import type { Metadata } from "next";
import { TrustHeader } from "@/components/trust/trust-header";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { ShieldAlert, Radio, Cpu, Layers, ArrowRight, Lock, Activity, CheckCircle2 } from "lucide-react";

export const metadata: Metadata = {
  title: "Vulnova | Enterprise AI Application Security Platform",
  description:
    "Continuous attack surface discovery, container sandbox DAST orchestration, and autonomous AI vulnerability intelligence for modern enterprise engineering.",
  openGraph: {
    title: "Vulnova Enterprise AI Application Security",
    description: "Autonomous AppSec Orchestration & Container Sandbox Scanning Engine",
    url: "https://vulnova.com",
    siteName: "Vulnova",
    type: "website",
  },
};

export default function Home() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 font-sans antialiased selection:bg-red-500/30">
      <TrustHeader />

      <main className="max-w-7xl mx-auto px-6 py-16 space-y-20">
        {/* Hero Section */}
        <section className="text-center space-y-6 max-w-4xl mx-auto pt-6">
          <div className="inline-flex items-center space-x-2 rounded-full border border-red-500/30 bg-red-950/40 px-4 py-1.5 text-xs text-red-400 font-mono shadow-lg shadow-red-950/50">
            <Radio className="h-3.5 w-3.5 animate-ping text-red-500" />
            <span>ERA 7 • ENTERPRISE APPSEC PLATFORM</span>
          </div>

          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-tight">
            Autonomous AI Application Security <br className="hidden sm:inline" />
            <span className="bg-gradient-to-r from-red-500 via-rose-500 to-red-400 bg-clip-text text-transparent">
              Operating at Enterprise Scale
            </span>
          </h1>

          <p className="text-base sm:text-lg text-zinc-400 max-w-2xl mx-auto leading-relaxed">
            Continuous attack surface discovery, container-sandboxed scanning orchestration,
            and CVSS 4.0 AI reasoning engineered for modern security teams.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-4 pt-4">
            <a href="/dashboard">
              <Button variant="primary" size="lg" className="shadow-red-950/60">
                <span>Enter Analyst Portal</span>
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </a>
            <a href="/trust">
              <Button variant="outline" size="lg">
                <Lock className="mr-2 h-4 w-4 text-emerald-400" />
                <span>Enterprise Trust Center</span>
              </Button>
            </a>
          </div>
        </section>

        {/* Feature Grid Section */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <Card className="border-zinc-800 bg-zinc-950/80 hover:border-zinc-700 transition-all">
            <CardHeader>
              <div className="p-3 w-fit rounded-lg bg-red-950/50 text-red-400 border border-red-800/40 mb-3">
                <ShieldAlert className="h-6 w-6" />
              </div>
              <CardTitle className="text-lg font-bold">Distributed Scanning Sandbox</CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-zinc-400 leading-relaxed space-y-2">
              <p>
                Containerized scanner workers operating inside isolated sandboxes (UID 10001, read-only rootfs)
                with automated exponential backoff and Celery Beat schedule orchestration.
              </p>
              <div className="flex items-center space-x-1.5 text-emerald-400 font-mono pt-2">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>OWASP ASVS V17 Aligned</span>
              </div>
            </CardContent>
          </Card>

          <Card className="border-zinc-800 bg-zinc-950/80 hover:border-zinc-700 transition-all">
            <CardHeader>
              <div className="p-3 w-fit rounded-lg bg-amber-950/50 text-amber-400 border border-amber-800/40 mb-3">
                <Cpu className="h-6 w-6" />
              </div>
              <CardTitle className="text-lg font-bold">Autonomous AI Analyst</CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-zinc-400 leading-relaxed space-y-2">
              <p>
                Multi-agent LLM reasoning pipeline executing CVSS 4.0 severity scoring, exploit verification,
                deduplication hashing, and language-specific code remediation.
              </p>
              <div className="flex items-center space-x-1.5 text-emerald-400 font-mono pt-2">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>Zero False-Positive Target</span>
              </div>
            </CardContent>
          </Card>

          <Card className="border-zinc-800 bg-zinc-950/80 hover:border-zinc-700 transition-all">
            <CardHeader>
              <div className="p-3 w-fit rounded-lg bg-blue-950/50 text-blue-400 border border-blue-800/40 mb-3">
                <Activity className="h-6 w-6" />
              </div>
              <CardTitle className="text-lg font-bold">Real-Time SOC Dashboard</CardTitle>
            </CardHeader>
            <CardContent className="text-xs text-zinc-400 leading-relaxed space-y-2">
              <p>
                Analyst experience unifying composite risk scores (0–100), live WebSocket telemetry streams,
                severity distribution charts, and crown-jewel target risk rankings.
              </p>
              <div className="flex items-center space-x-1.5 text-emerald-400 font-mono pt-2">
                <CheckCircle2 className="h-3.5 w-3.5" />
                <span>Redis 30s Metric Caching</span>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Call-to-Action Footer Banner */}
        <section className="p-8 sm:p-12 rounded-2xl border border-zinc-800 bg-gradient-to-r from-zinc-900 via-zinc-950 to-zinc-900 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="space-y-2 text-left">
            <h3 className="text-xl sm:text-2xl font-extrabold text-white">
              Ready to Explore Vulnova Enterprise Architecture?
            </h3>
            <p className="text-xs sm:text-sm text-zinc-400">
              Access the Trust Center for security disclosures or launch the SOC Analyst Portal.
            </p>
          </div>

          <div className="flex items-center space-x-4">
            <a href="/trust">
              <Button variant="secondary" size="md">
                Trust Center
              </Button>
            </a>
            <a href="/dashboard">
              <Button variant="primary" size="md">
                Launch Portal
              </Button>
            </a>
          </div>
        </section>
      </main>
    </div>
  );
}
