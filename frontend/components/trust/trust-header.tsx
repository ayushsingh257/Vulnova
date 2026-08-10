"use client";

import * as React from "react";
import Link from "next/link";
import { ShieldAlert, ShieldCheck, ArrowRight, Lock, LogIn, UserPlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StatusWidget } from "@/components/trust/status-widget";

export function TrustHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-zinc-800/80 bg-zinc-950/80 backdrop-blur-xl px-6 py-4 flex items-center justify-between shadow-2xl">
      <div className="flex items-center space-x-6">
        <Link href="/" className="flex items-center space-x-2.5 group">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-red-600/20 border border-red-500/40 text-red-500 shadow-md shadow-red-950/50 transition-transform group-hover:scale-105">
            <ShieldAlert className="h-5 w-5 animate-pulse" />
          </div>
          <div>
            <span className="text-lg font-extrabold tracking-wider text-white">VULNOVA</span>
            <span className="ml-2 rounded-full border border-red-500/30 bg-red-950/40 px-2 py-0.5 text-[10px] font-semibold text-red-400">
              SOC ENTERPRISE
            </span>
          </div>
        </Link>

        <nav className="hidden md:flex items-center space-x-4 border-l border-zinc-800 pl-6 text-xs font-medium text-zinc-400">
          <Link href="/trust" className="hover:text-zinc-100 transition-colors flex items-center space-x-1.5">
            <ShieldCheck className="h-3.5 w-3.5 text-red-400" />
            <span>Trust Center</span>
          </Link>
          <Link href="/security" className="hover:text-zinc-100 transition-colors flex items-center space-x-1.5">
            <ShieldAlert className="h-3.5 w-3.5 text-zinc-400" />
            <span>Vulnerability Disclosure</span>
          </Link>
          <a
            href="/.well-known/security.txt"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-zinc-100 transition-colors flex items-center space-x-1.5 font-mono text-[11px]"
          >
            <Lock className="h-3 w-3 text-emerald-400" />
            <span>security.txt</span>
          </a>
        </nav>
      </div>

      <div className="flex items-center space-x-3">
        <StatusWidget status="OPERATIONAL" />

        <Link
          href="/login"
          className="hidden sm:inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-zinc-800 bg-zinc-900 text-xs font-semibold text-zinc-300 hover:bg-zinc-800 hover:text-white transition-colors"
        >
          <LogIn className="h-3.5 w-3.5 text-zinc-400" />
          <span>Sign In</span>
        </Link>

        <Link href="/signup">
          <Button variant="primary" size="sm" className="hidden sm:inline-flex">
            <span>Request Access</span>
            <ArrowRight className="ml-1.5 h-3.5 w-3.5" />
          </Button>
        </Link>
      </div>
    </header>
  );
}
