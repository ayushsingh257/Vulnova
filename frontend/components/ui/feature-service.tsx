"use client";

import React from "react";
import {
  ShieldAlert,
  Cpu,
  ArrowRight,
  Server,
  FileCheck2,
  Lock,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export const FeatureServices = () => {
  return (
    <section className="py-24 px-6 bg-zinc-950 border-t border-zinc-900/80 font-sans">
      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-16 items-center">
        <div className="lg:col-span-4">
          <span className="px-4 py-1.5 rounded-md border border-red-500/30 bg-red-950/40 text-xs font-bold uppercase tracking-widest text-red-400 mb-5 inline-block">
            Autonomous Capabilities
          </span>
          <h2 className="text-4xl font-bold text-white mb-5 text-balance tracking-tight leading-tight">
            Enterprise Security Services Engine
          </h2>
          <p className="text-zinc-400 text-lg leading-relaxed text-pretty mb-10">
            Engineered for modern security operations, Vulnova combines sandboxed execution, continuous asset discovery, and AI reasoning to eliminate security blind spots.
          </p>
          <a href="/signup">
            <Button className="bg-red-600 text-white px-8 py-3 rounded-lg font-bold flex items-center gap-2 hover:bg-red-500 transition-all active:scale-95 shadow-xl shadow-red-950/50 border border-red-500/40">
              Get Started <ArrowRight className="size-4" />
            </Button>
          </a>
        </div>

        <div className="lg:col-span-8 grid grid-cols-1 md:grid-cols-2 gap-6">
          <ServiceCard
            icon={Cpu}
            title="Autonomous AI Analyst"
            desc="Multi-agent LLM reasoning for automated CVSS vector intelligence, root cause explanation, and framework-specific patch diff generation."
            active
          />
          <ServiceCard
            icon={ShieldAlert}
            title="Attack Surface Mapping"
            desc="Continuous asset surface discovery, technology stack fingerprinting, and threat exposure graph correlation."
          />
          <ServiceCard
            icon={Server}
            title="Container Sandbox Isolation"
            desc="Ephemeral non-root worker execution, CPU/memory resource quotas, read-only rootfs, and RFC1918 egress blocklists."
          />
          <ServiceCard
            icon={FileCheck2}
            title="Evidence Quarantine Pipeline"
            desc="ClamAV TCP socket streaming, YARA static malware analysis, and dual-bucket staging for non-repudiable evidence integrity."
          />
        </div>
      </div>
    </section>
  );
};

const ServiceCard = ({ icon: Icon, title, desc, active }: any) => (
  <div
    className={cn(
      "p-10 rounded-2xl transition-all duration-300 flex flex-col gap-6",
      active
        ? "bg-gradient-to-b from-red-950/80 to-zinc-950 text-white border border-red-500/50 shadow-2xl shadow-red-950/40"
        : "bg-zinc-900/60 text-zinc-200 border border-zinc-800 hover:border-red-500/30 hover:bg-zinc-900/90"
    )}
  >
    <div
      className={cn(
        "size-12 rounded-full flex items-center justify-center",
        active ? "bg-red-600 text-white shadow-lg shadow-red-950/60" : "bg-red-950/60 text-red-400 border border-red-900/50"
      )}
    >
      <Icon className="size-5" />
    </div>
    <div className="space-y-4">
      <h3 className="text-2xl font-semibold tracking-tight text-white">{title}</h3>
      <p
        className={cn(
          "text-sm leading-relaxed text-pretty",
          active ? "text-zinc-300" : "text-zinc-400"
        )}
      >
        {desc}
      </p>
    </div>
  </div>
);

export default FeatureServices;
