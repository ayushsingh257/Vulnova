import * as React from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { TrustHeader } from "@/components/trust/trust-header";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import DotPattern from "@/components/ui/dot-pattern-1";
import FeatureServices from "@/components/ui/feature-service";
import {
  ShieldAlert,
  Radio,
  Cpu,
  Layers,
  ArrowRight,
  Lock,
  Activity,
  CheckCircle2,
  Server,
  FileCheck2,
  ShieldCheck,
  Zap,
  Users,
  Terminal,
  Database,
  Building2,
  Code2,
  KeyRound,
  FileText,
  Workflow,
  XCircle,
} from "lucide-react";

export const metadata: Metadata = {
  title: "Vulnova | Autonomous AI Application Security Platform",
  description:
    "Enterprise AI-powered application security platform providing autonomous vulnerability intelligence, attack surface discovery, secure scanning, and SOC workflows.",
  openGraph: {
    title: "Vulnova | Autonomous AI Application Security Platform",
    description:
      "Enterprise AI-powered application security platform providing autonomous vulnerability intelligence, attack surface discovery, secure scanning, and SOC workflows.",
    url: "https://vulnova.com",
    siteName: "Vulnova Security",
    type: "website",
  },
};

export default function Home() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 font-sans antialiased selection:bg-red-500/30 selection:text-red-200">
      {/* Primary Enterprise Navbar */}
      <TrustHeader />

      {/* Main Page Flow */}
      <main className="space-y-24 pb-20">
        
        {/* 1. Hero Section */}
        <section id="platform" className="relative pt-20 pb-16 px-6 max-w-7xl mx-auto overflow-hidden">
          {/* Subtle Ambient Red Glow Effects */}
          <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-red-600/10 blur-[140px] pointer-events-none rounded-full" />

          <div className="relative z-10 text-center space-y-8 max-w-5xl mx-auto">
            <div className="inline-flex items-center space-x-2.5 rounded-full border border-red-500/40 bg-red-950/60 px-4 py-1.5 text-xs text-red-400 font-mono shadow-xl shadow-red-950/60">
              <Radio className="h-3.5 w-3.5 animate-pulse text-red-500" />
              <span>VULNOVA v1.0.1 • ENTERPRISE AI SECURITY PLATFORM</span>
            </div>

            <h1 className="text-4xl sm:text-6xl md:text-7xl font-extrabold tracking-tight text-white leading-[1.1]">
              Autonomous AI Security Operations <br className="hidden sm:inline" />
              <span className="bg-gradient-to-r from-red-500 via-rose-500 to-red-400 bg-clip-text text-transparent">
                for Modern Enterprises
              </span>
            </h1>

            <p className="text-base sm:text-xl text-zinc-400 max-w-3xl mx-auto leading-relaxed text-balance">
              Unified attack surface discovery, container-sandboxed scanning orchestration, 
              CVSS 4.0 AI reasoning, and automated code remediation engineered for enterprise security operations.
            </p>

            {/* CTAs */}
            <div className="flex flex-wrap items-center justify-center gap-4 pt-4">
              <Link href="/signup">
                <Button variant="primary" size="lg" className="h-12 px-8 text-base shadow-xl shadow-red-950/80">
                  <span>Request Enterprise Access</span>
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
              <Link href="#capabilities">
                <Button variant="outline" size="lg" className="h-12 px-8 text-base border-zinc-800 bg-zinc-900/60 hover:bg-zinc-900 hover:text-white">
                  <span>Explore Platform Capabilities</span>
                </Button>
              </Link>
            </div>

            {/* Live Operational Metrics Ribbon */}
            <div className="pt-10 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-4xl mx-auto border-t border-zinc-900/80">
              <div className="p-4 rounded-xl border border-zinc-900 bg-zinc-950/60 backdrop-blur">
                <div className="text-2xl font-extrabold text-white font-mono">733 / 733</div>
                <div className="text-xs text-zinc-500 font-medium uppercase tracking-wider mt-1">Verified Test Suite</div>
              </div>
              <div className="p-4 rounded-xl border border-zinc-900 bg-zinc-950/60 backdrop-blur">
                <div className="text-2xl font-extrabold text-red-500 font-mono">CVSS v4.0</div>
                <div className="text-xs text-zinc-500 font-medium uppercase tracking-wider mt-1">AI Reasoning Engine</div>
              </div>
              <div className="p-4 rounded-xl border border-zinc-900 bg-zinc-950/60 backdrop-blur">
                <div className="text-2xl font-extrabold text-white font-mono">UID 10001</div>
                <div className="text-xs text-zinc-500 font-medium uppercase tracking-wider mt-1">Sandbox Isolation</div>
              </div>
              <div className="p-4 rounded-xl border border-zinc-900 bg-zinc-950/60 backdrop-blur">
                <div className="text-2xl font-extrabold text-emerald-400 font-mono">100%</div>
                <div className="text-xs text-zinc-500 font-medium uppercase tracking-wider mt-1">OWASP Top 10 Aligned</div>
              </div>
            </div>
          </div>
        </section>

        {/* 2. Interactive Red-Accented Quote Banner (DotPattern Integration) */}
        <section className="mx-auto max-w-7xl px-6">
          <div className="relative flex flex-col items-center border border-red-500/50 bg-zinc-950 rounded-2xl overflow-hidden shadow-2xl shadow-red-950/30">
            <DotPattern width={24} height={24} className="fill-red-500/15" />

            {/* Corner Red Accent Boxes */}
            <div className="absolute -left-1.5 -top-1.5 h-3.5 w-3.5 bg-red-600 text-white shadow-md shadow-red-500" />
            <div className="absolute -bottom-1.5 -left-1.5 h-3.5 w-3.5 bg-red-600 text-white shadow-md shadow-red-500" />
            <div className="absolute -right-1.5 -top-1.5 h-3.5 w-3.5 bg-red-600 text-white shadow-md shadow-red-500" />
            <div className="absolute -bottom-1.5 -right-1.5 h-3.5 w-3.5 bg-red-600 text-white shadow-md shadow-red-500" />

            <div className="relative z-20 mx-auto max-w-5xl text-center py-12 px-6 md:px-12 md:py-16">
              <p className="text-xs md:text-sm font-bold uppercase tracking-widest text-red-500 mb-4">
                THE VULNOVA DEFENSE PHILOSOPHY
              </p>
              <div className="text-xl md:text-3xl lg:text-4xl font-extrabold tracking-tight leading-relaxed text-zinc-100">
                <span className="text-red-500">&quot;Autonomous AI defense</span> is not about replacing human security engineers &mdash; it is about empowering SOC teams to analyze, verify, and remediate vulnerabilities at <span className="text-white underline decoration-red-500/60 underline-offset-8">machine speed</span> before adversaries can exploit them.&quot;
              </div>
            </div>
          </div>
        </section>

        {/* 3. Product Story ("What is Vulnova?") */}
        <section className="max-w-7xl mx-auto px-6 pt-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
            
            <div className="lg:col-span-6 space-y-6">
              <span className="px-3.5 py-1.5 rounded-md border border-red-500/30 bg-red-950/40 text-xs font-bold uppercase tracking-widest text-red-400">
                The AppSec Challenge
              </span>
              <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight leading-tight">
                Why Traditional Application Security Tools Fail Enterprise SOCs
              </h2>
              <p className="text-zinc-400 text-base leading-relaxed">
                Legacy Dynamic Application Security Testing (DAST) scanners flood security teams with thousands of low-context alerts while missing complex single-page apps (SPAs) and dynamic REST/GraphQL API surfaces.
              </p>
              
              <div className="space-y-4 pt-2">
                <div className="flex items-start space-x-3 p-4 rounded-xl border border-zinc-900 bg-zinc-950">
                  <XCircle className="h-5 w-5 text-red-500 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="text-sm font-bold text-white">Alert Fatigue & Noise</h4>
                    <p className="text-xs text-zinc-400 mt-1">Security analysts waste 60%+ of their triage bandwidth validating false positives with no business risk context.</p>
                  </div>
                </div>

                <div className="flex items-start space-x-3 p-4 rounded-xl border border-zinc-900 bg-zinc-950">
                  <XCircle className="h-5 w-5 text-red-500 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="text-sm font-bold text-white">Unprotected Scanner Infrastructure</h4>
                    <p className="text-xs text-zinc-400 mt-1">Unsanitized DAST payloads risk executing dangerous operations directly against internal enterprise networks.</p>
                  </div>
                </div>

                <div className="flex items-start space-x-3 p-4 rounded-xl border border-zinc-900 bg-zinc-950">
                  <XCircle className="h-5 w-5 text-red-500 shrink-0 mt-0.5" />
                  <div>
                    <h4 className="text-sm font-bold text-white">No Actionable Code Fixes</h4>
                    <p className="text-xs text-zinc-400 mt-1">Traditional tools dump generic CVE text descriptions onto developers without verified, framework-specific code patches.</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Vulnova Autonomous Solution Card */}
            <div className="lg:col-span-6 p-8 rounded-2xl border border-red-500/40 bg-gradient-to-b from-red-950/40 via-zinc-950 to-zinc-950 shadow-2xl shadow-red-950/30 space-y-6">
              <div className="flex items-center space-x-3">
                <div className="p-3 rounded-lg bg-red-600/20 border border-red-500/40 text-red-500">
                  <ShieldCheck className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-white">The Vulnova Autonomous Solution</h3>
                  <p className="text-xs text-red-400 font-mono mt-0.5">AI-Native Control Plane</p>
                </div>
              </div>

              <p className="text-sm text-zinc-300 leading-relaxed">
                Vulnova unifies target surface discovery, ephemeral container sandbox scanning, multi-agent AI verification, and verified code remediation under a single enterprise control plane.
              </p>

              <ul className="space-y-3 text-xs text-zinc-300">
                <li className="flex items-center space-x-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                  <span>Autonomous AI analysis computing CVSS 4.0 severity scores & proof verifications</span>
                </li>
                <li className="flex items-center space-x-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                  <span>Container-sandboxed workers (`UID 10001`, `read_only_rootfs`, network egress blocklists)</span>
                </li>
                <li className="flex items-center space-x-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                  <span>Verified code patch diff generation for Python, JavaScript, Go, Java, Docker, Nginx</span>
                </li>
                <li className="flex items-center space-x-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                  <span>ClamAV TCP socket streaming & YARA static malware quarantine protection</span>
                </li>
              </ul>

              <div className="pt-4 border-t border-zinc-900">
                <Link href="/trust">
                  <Button variant="secondary" size="md" className="w-full justify-center">
                    <span>View Enterprise Security Architecture</span>
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </Link>
              </div>
            </div>

          </div>
        </section>

        {/* 4. Enterprise Security Capabilities (FeatureServices Integration) */}
        <div id="capabilities">
          <FeatureServices />
        </div>

        {/* 5. Competitive Differentiation ("Why Vulnova is Different") */}
        <section className="max-w-7xl mx-auto px-6">
          <div className="text-center space-y-4 max-w-3xl mx-auto mb-14">
            <span className="px-3.5 py-1.5 rounded-md border border-red-500/30 bg-red-950/40 text-xs font-bold uppercase tracking-widest text-red-400">
              Architectural Leadership
            </span>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Why Enterprise SOCs Choose Vulnova
            </h2>
            <p className="text-zinc-400 text-sm sm:text-base">
              Comparing traditional legacy scanning tools against Vulnova&apos;s autonomous AI security operations model.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* Traditional AppSec */}
            <div className="p-8 rounded-2xl border border-zinc-900 bg-zinc-950 space-y-6">
              <div className="flex items-center space-x-3">
                <div className="p-2.5 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-500">
                  <XCircle className="h-5 w-5" />
                </div>
                <h3 className="text-xl font-bold text-zinc-400">Legacy AppSec Scanners</h3>
              </div>
              
              <ul className="space-y-4 text-xs text-zinc-400">
                <li className="p-3.5 rounded-xl border border-zinc-900 bg-zinc-900/40">
                  <strong className="text-zinc-300 block mb-1">Manual Alert Triage:</strong> Analysts manually review every alert without contextual impact prioritization.
                </li>
                <li className="p-3.5 rounded-xl border border-zinc-900 bg-zinc-900/40">
                  <strong className="text-zinc-300 block mb-1">Unprotected Execution:</strong> Scanner workers execute direct network traffic from root hosts with no sandbox boundaries.
                </li>
                <li className="p-3.5 rounded-xl border border-zinc-900 bg-zinc-900/40">
                  <strong className="text-zinc-300 block mb-1">Generic Descriptions:</strong> Outputs text descriptions of vulnerabilities requiring engineering teams to write fixes from scratch.
                </li>
                <li className="p-3.5 rounded-xl border border-zinc-900 bg-zinc-900/40">
                  <strong className="text-zinc-300 block mb-1">Siloed Reports:</strong> Disconnected CSV/PDF files with zero real-time WebSocket streams or live posture velocity tracking.
                </li>
              </ul>
            </div>

            {/* Vulnova Autonomous Security */}
            <div className="p-8 rounded-2xl border border-red-500/50 bg-gradient-to-b from-red-950/30 to-zinc-950 shadow-xl shadow-red-950/30 space-y-6">
              <div className="flex items-center space-x-3">
                <div className="p-2.5 rounded-lg bg-red-600/20 border border-red-500/40 text-red-500">
                  <ShieldCheck className="h-5 w-5" />
                </div>
                <h3 className="text-xl font-bold text-white">Vulnova Autonomous Platform</h3>
              </div>

              <ul className="space-y-4 text-xs text-zinc-200">
                <li className="p-3.5 rounded-xl border border-red-500/30 bg-red-950/30">
                  <strong className="text-white block mb-1">AI-Assisted Investigation:</strong> Multi-agent LLM reasoning computes confidence scores (LOW to CONFIRMED) and filters noise.
                </li>
                <li className="p-3.5 rounded-xl border border-red-500/30 bg-red-950/30">
                  <strong className="text-white block mb-1">Sandboxed Scanning:</strong> Ephemeral container sandboxes (`UID 10001`, `CAP_DROP_ALL`, read-only rootfs, RFC1918 blocklists).
                </li>
                <li className="p-3.5 rounded-xl border border-red-500/30 bg-red-950/30">
                  <strong className="text-white block mb-1">Actionable Code Patches:</strong> Generates verified code/config patch diffs (`Python`, `JS`, `Go`, `Java`, `Docker`, `Nginx`) for single-click review.
                </li>
                <li className="p-3.5 rounded-xl border border-red-500/30 bg-red-950/30">
                  <strong className="text-white block mb-1">Unified Control Plane:</strong> Real-time SOC dashboard, WebSocket telemetry streams, CISO PDF exports, and Jira/GitHub bi-directional sync.
                </li>
              </ul>
            </div>
          </div>
        </section>

        {/* 6. Enterprise Use Cases ("Built for Security Teams") */}
        <section className="max-w-7xl mx-auto px-6">
          <div className="text-center space-y-4 max-w-3xl mx-auto mb-14">
            <span className="px-3.5 py-1.5 rounded-md border border-red-500/30 bg-red-950/40 text-xs font-bold uppercase tracking-widest text-red-400">
              Enterprise Personas
            </span>
            <h2 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Engineered for Modern Security Organizations
            </h2>
            <p className="text-zinc-400 text-sm sm:text-base">
              Tailored capabilities providing value across SOC analysts, security engineers, CISOs, and DevSecOps teams.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div className="p-6 rounded-2xl border border-zinc-900 bg-zinc-950 hover:border-red-500/40 transition-all space-y-4">
              <div className="p-3 w-fit rounded-lg bg-red-950/60 text-red-400 border border-red-900/50">
                <Users className="h-5 w-5" />
              </div>
              <h3 className="text-lg font-bold text-white">SOC Analysts</h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Real-time threat anomaly clustering, immutable audit log attribution, live WebSocket scan streaming, and automated ticket creation.
              </p>
            </div>

            <div className="p-6 rounded-2xl border border-zinc-900 bg-zinc-950 hover:border-red-500/40 transition-all space-y-4">
              <div className="p-3 w-fit rounded-lg bg-red-950/60 text-red-400 border border-red-900/50">
                <ShieldAlert className="h-5 w-5" />
              </div>
              <h3 className="text-lg font-bold text-white">Security Engineers</h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Cryptographically signed Ed25519 plugin execution, DNS TXT domain verification challenges, and custom scan profile policies.
              </p>
            </div>

            <div className="p-6 rounded-2xl border border-zinc-900 bg-zinc-950 hover:border-red-500/40 transition-all space-y-4">
              <div className="p-3 w-fit rounded-lg bg-red-950/60 text-red-400 border border-red-900/50">
                <Building2 className="h-5 w-5" />
              </div>
              <h3 className="text-lg font-bold text-white">CISOs & Leadership</h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Executive CISO PDF reports, posture risk scores (0–100), and automated compliance mapping for OWASP, ASVS, PCI DSS, and ISO 27001.
              </p>
            </div>

            <div className="p-6 rounded-2xl border border-zinc-900 bg-zinc-950 hover:border-red-500/40 transition-all space-y-4">
              <div className="p-3 w-fit rounded-lg bg-red-950/60 text-red-400 border border-red-900/50">
                <Terminal className="h-5 w-5" />
              </div>
              <h3 className="text-lg font-bold text-white">DevSecOps Teams</h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Standalone `vulnova-cli` build security gates, GitHub Actions / GitLab CI templates, and Jira & GitHub Issues synchronization.
              </p>
            </div>
          </div>
        </section>

        {/* 7. Technical Architecture Showcase */}
        <section id="architecture" className="max-w-7xl mx-auto px-6">
          <div className="p-8 sm:p-12 rounded-2xl border border-zinc-800 bg-zinc-900/40 backdrop-blur-xl space-y-10">
            <div className="text-center space-y-3 max-w-3xl mx-auto">
              <span className="px-3.5 py-1.5 rounded-md border border-red-500/30 bg-red-950/40 text-xs font-bold uppercase tracking-widest text-red-400">
                Enterprise Infrastructure
              </span>
              <h2 className="text-3xl font-extrabold text-white">
                Powered by Production-Grade Open Stack Architecture
              </h2>
              <p className="text-xs sm:text-sm text-zinc-400">
                Designed for high concurrency, zero data leakage, and seamless cloud deployment.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 text-xs">
              <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-950 space-y-3">
                <div className="flex items-center space-x-2 text-red-400 font-bold">
                  <Code2 className="h-4 w-4" />
                  <span>Frontend Cockpit</span>
                </div>
                <ul className="text-zinc-400 space-y-1 font-mono text-[11px]">
                  <li>Next.js 14 (App Router)</li>
                  <li>React 18 & TypeScript</li>
                  <li>Tailwind CSS & Lucide</li>
                  <li>Standalone Build Export</li>
                </ul>
              </div>

              <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-950 space-y-3">
                <div className="flex items-center space-x-2 text-red-400 font-bold">
                  <Server className="h-4 w-4" />
                  <span>Backend Control Plane</span>
                </div>
                <ul className="text-zinc-400 space-y-1 font-mono text-[11px]">
                  <li>FastAPI & AsyncIO</li>
                  <li>Python 3.13 & Pydantic v2</li>
                  <li>SQLAlchemy 2.0 (Async)</li>
                  <li>49 REST Router Modules</li>
                </ul>
              </div>

              <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-950 space-y-3">
                <div className="flex items-center space-x-2 text-red-400 font-bold">
                  <Cpu className="h-4 w-4" />
                  <span>AI & Vector Intelligence</span>
                </div>
                <ul className="text-zinc-400 space-y-1 font-mono text-[11px]">
                  <li>Multi-Agent LLM Reasoning</li>
                  <li>RAG Knowledge Engine</li>
                  <li>Qdrant Vector Storage</li>
                  <li>Security Knowledge Graphs</li>
                </ul>
              </div>

              <div className="p-5 rounded-xl border border-zinc-800 bg-zinc-950 space-y-3">
                <div className="flex items-center space-x-2 text-red-400 font-bold">
                  <Database className="h-4 w-4" />
                  <span>Security & Storage</span>
                </div>
                <ul className="text-zinc-400 space-y-1 font-mono text-[11px]">
                  <li>PostgreSQL 16 & Redis 7</li>
                  <li>Celery Worker Cluster</li>
                  <li>MinIO Evidence Storage</li>
                  <li>ClamAV TCP & YARA Engine</li>
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* 8. Conversion CTA Footer Banner */}
        <section className="max-w-7xl mx-auto px-6">
          <div className="p-10 sm:p-14 rounded-2xl border border-red-500/40 bg-gradient-to-r from-red-950/60 via-zinc-950 to-zinc-950 shadow-2xl shadow-red-950/40 flex flex-col md:flex-row items-center justify-between gap-8">
            <div className="space-y-3 text-left max-w-2xl">
              <span className="px-3 py-1 rounded border border-red-500/30 bg-red-950/50 text-[11px] font-bold text-red-400 uppercase tracking-widest">
                Production Deployment Ready
              </span>
              <h3 className="text-2xl sm:text-3xl font-extrabold text-white">
                Ready to Automate Enterprise Application Security?
              </h3>
              <p className="text-xs sm:text-sm text-zinc-400 leading-relaxed">
                Deploy Vulnova v1.0.1 in your cloud environment or launch the live Security Operations Command Center.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-4 shrink-0">
              <Link href="/trust">
                <Button variant="secondary" size="lg" className="h-11 border-zinc-800">
                  <ShieldCheck className="mr-2 h-4 w-4 text-red-400" />
                  <span>Trust Center</span>
                </Button>
              </Link>
              <Link href="/dashboard">
                <Button variant="primary" size="lg" className="h-11 shadow-lg shadow-red-950/80">
                  <span>Launch SOC Portal</span>
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </div>
          </div>
        </section>

      </main>

      {/* Enterprise Footer */}
      <footer className="border-t border-zinc-900 bg-zinc-950 px-6 py-12 text-xs text-zinc-500">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center space-x-3">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-red-600/20 border border-red-500/40 text-red-500">
              <ShieldAlert className="h-4 w-4" />
            </div>
            <div>
              <span className="font-bold text-white">VULNOVA</span>
              <span className="ml-2 text-zinc-500">v1.0.1 Enterprise Release</span>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-6 font-medium text-zinc-400">
            <Link href="/trust" className="hover:text-white transition-colors">Trust Center</Link>
            <Link href="/security" className="hover:text-white transition-colors">Vulnerability Disclosure</Link>
            <a href="/.well-known/security.txt" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors font-mono">security.txt</a>
            <Link href="/compliance" className="hover:text-white transition-colors">Compliance Frameworks</Link>
            <Link href="/login" className="hover:text-white transition-colors">Sign In</Link>
          </div>

          <div className="text-zinc-600 text-center md:text-right">
            © 2026 Vulnova Enterprise Security Inc. All rights reserved.
          </div>
        </div>
      </footer>
    </div>
  );
}
