"use client";

import * as React from "react";
import { Mail, Key, FileText, ExternalLink, ShieldAlert } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export function SecurityDisclosureCard() {
  return (
    <Card className="border-zinc-800 bg-zinc-950/80">
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <div className="flex items-center space-x-2">
          <ShieldAlert className="h-5 w-5 text-red-500" />
          <CardTitle className="text-lg font-bold">Vulnerability Disclosure Policy (RFC 9116)</CardTitle>
        </div>
        <span className="text-xs text-zinc-400 font-mono">
          Responsible Disclosure Guidelines
        </span>
      </CardHeader>

      <CardContent className="space-y-6">
        <p className="text-xs text-zinc-300 leading-relaxed">
          Vulnova welcomes vulnerability reports from security researchers, penetration testers, and community auditors.
          We are committed to resolving verified security issues rapidly and protecting researchers operating in good faith.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="p-3.5 rounded-xl border border-zinc-800/80 bg-zinc-900/40 space-y-1">
            <div className="text-zinc-400 font-semibold flex items-center space-x-1.5">
              <Mail className="h-4 w-4 text-red-400" />
              <span>Security Contact Email</span>
            </div>
            <a href="mailto:security@vulnova.com" className="font-mono text-zinc-100 font-bold hover:underline block">
              security@vulnova.com
            </a>
          </div>

          <div className="p-3.5 rounded-xl border border-zinc-800/80 bg-zinc-900/40 space-y-1">
            <div className="text-zinc-400 font-semibold flex items-center space-x-1.5">
              <Key className="h-4 w-4 text-amber-400" />
              <span>PGP Public Key</span>
            </div>
            <a href="/security.asc" className="font-mono text-zinc-100 font-bold hover:underline block">
              vulnova.com/security.asc
            </a>
          </div>

          <div className="p-3.5 rounded-xl border border-zinc-800/80 bg-zinc-900/40 space-y-1">
            <div className="text-zinc-400 font-semibold flex items-center space-x-1.5">
              <FileText className="h-4 w-4 text-emerald-400" />
              <span>RFC 9116 Specification</span>
            </div>
            <a
              href="/.well-known/security.txt"
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-emerald-400 font-bold hover:underline block"
            >
              /.well-known/security.txt
            </a>
          </div>
        </div>

        <div className="pt-4 border-t border-zinc-800/60 flex items-center justify-between">
          <span className="text-xs text-zinc-400">
            Preferred Languages: <strong className="text-zinc-200">English, Spanish</strong>
          </span>
          <a href="/security">
            <Button variant="outline" size="sm">
              <span>View Full Disclosure SLA</span>
              <ExternalLink className="ml-1.5 h-3.5 w-3.5" />
            </Button>
          </a>
        </div>
      </CardContent>
    </Card>
  );
}
