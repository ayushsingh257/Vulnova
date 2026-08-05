"use client";

import React from "react";
import { Shield, Lock, FileCheck, Layers } from "lucide-react";

export interface FrameworkOption {
  id: string;
  name: string;
  version: string;
  icon: React.ElementType;
}

export const FRAMEWORKS: FrameworkOption[] = [
  {
    id: "owasp_top10",
    name: "OWASP Top 10",
    version: "OWASP Top 10 2021",
    icon: Shield,
  },
  {
    id: "asvs_v4",
    name: "OWASP ASVS",
    version: "OWASP ASVS 4.0.3",
    icon: FileCheck,
  },
  {
    id: "pci_dss",
    name: "PCI-DSS",
    version: "PCI DSS 4.0",
    icon: Lock,
  },
  {
    id: "iso27001",
    name: "ISO 27001",
    version: "ISO 27001:2022",
    icon: Layers,
  },
];

interface FrameworkSelectorProps {
  activeFramework: string;
  onSelect: (frameworkId: string) => void;
}

export const FrameworkSelector: React.FC<FrameworkSelectorProps> = ({
  activeFramework,
  onSelect,
}) => {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {FRAMEWORKS.map((fw) => {
        const Icon = fw.icon;
        const isActive = activeFramework === fw.id;
        return (
          <button
            key={fw.id}
            onClick={() => onSelect(fw.id)}
            className={`flex items-center space-x-3 rounded-xl border p-4 text-left transition-all duration-200 ${
              isActive
                ? "border-red-500/60 bg-red-950/30 text-white shadow-lg shadow-red-950/40 ring-1 ring-red-500/50"
                : "border-zinc-800 bg-zinc-950/60 text-zinc-400 hover:border-zinc-700 hover:bg-zinc-900/60 hover:text-zinc-200"
            }`}
          >
            <div
              className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border ${
                isActive
                  ? "border-red-500/40 bg-red-600/20 text-red-400"
                  : "border-zinc-800 bg-zinc-900 text-zinc-400"
              }`}
            >
              <Icon className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <div className="text-sm font-bold truncate">{fw.name}</div>
              <div className="text-[10px] font-mono text-zinc-500 truncate mt-0.5">
                {fw.version}
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
};
