"use client";

import * as React from "react";
import Link from "next/link";
import { ShieldAlert, ShieldCheck, ArrowRight, LogIn, Cpu, Layers, BookOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StatusWidget } from "@/components/trust/status-widget";

export function TrustHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-zinc-800/80 bg-zinc-950/90 backdrop-blur-xl px-6 py-4 flex items-center justify-between shadow-2xl">
      <div className="flex items-center space-x-6">
        <Link href="/" className="flex items-center space-x-2.5 group">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-red-600/20 border border-red-500/40 text-red-500 shadow-md shadow-red-950/50 transition-transform group-hover:scale-105">
            <ShieldAlert className="h-5 w-5 animate-pulse" />
          </div>
          <div>
            <span className="text-lg font-extrabold tracking-wider text-white">VULNOVA</span>
            <span className="ml-2 rounded-full border border-red-500/30 bg-red-950/50 px-2 py-0.5 text-[10px] font-semibold text-red-400">
              v1.0.1
            </span>
          </div>
        </Link>

        <nav className="hidden lg:flex items-center space-x-5 border-l border-zinc-800 pl-6 text-xs font-medium text-zinc-400">
          <Link href="/#platform" className="hover:text-zinc-100 transition-colors flex items-center space-x-1.5">
            <Cpu className="h-3.5 w-3.5 text-red-500" />
            <span>Platform</span>
          </Link>
          <Link href="/#capabilities" className="hover:text-zinc-100 transition-colors flex items-center space-x-1.5">
            <Layers className="h-3.5 w-3.5 text-zinc-400" />
            <span>Capabilities</span>
          </Link>
          <Link href="/trust" className="hover:text-zinc-100 transition-colors flex items-center space-x-1.5">
            <ShieldCheck className="h-3.5 w-3.5 text-red-400" />
            <span>Trust Center</span>
          </Link>
          <Link href="/security" className="hover:text-zinc-100 transition-colors flex items-center space-x-1.5">
            <ShieldAlert className="h-3.5 w-3.5 text-zinc-400" />
            <span>Security</span>
          </Link>
          <Link href="/#architecture" className="hover:text-zinc-100 transition-colors flex items-center space-x-1.5">
            <BookOpen className="h-3.5 w-3.5 text-zinc-400" />
            <span>Architecture</span>
          </Link>
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
