import * as React from "react";
import type { Metadata } from "next";
import { TrustHeader } from "@/components/trust/trust-header";
import { SecurityDisclosureCard } from "@/components/trust/security-disclosure-card";
import { ShieldCheck, Lock, Mail, Clock, AlertTriangle, CheckCircle2 } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export const metadata: Metadata = {
  title: "Vulnerability Disclosure Policy & RFC 9116 | Vulnova",
  description:
    "Vulnova's Responsible Vulnerability Disclosure Policy, PGP encryption key, security contact email (security@vulnova.com), and response SLAs.",
  openGraph: {
    title: "Vulnova Vulnerability Disclosure Policy",
    description: "Responsible Disclosure SLAs, PGP Public Key, and RFC 9116 security.txt",
    url: "https://vulnova.com/security",
    siteName: "Vulnova Security",
    type: "website",
  },
};

export default function SecurityDisclosurePage() {
  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 font-sans antialiased selection:bg-red-500/30">
      <TrustHeader />

      <main className="max-w-5xl mx-auto px-6 py-12 space-y-10">
        {/* Header */}
        <section className="text-center space-y-3">
          <div className="inline-flex items-center space-x-2 rounded-full border border-emerald-500/30 bg-emerald-950/40 px-3 py-1 text-xs text-emerald-400 font-mono">
            <span>RFC 9116 COMPLIANT DISCLOSURE POLICY</span>
          </div>
          <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white">
            Vulnerability Disclosure & Security Policy
          </h1>
          <p className="text-sm text-zinc-400 max-w-2xl mx-auto">
            Our guidelines for security researchers operating in good faith to identify and report potential security vulnerabilities.
          </p>
        </section>

        {/* Card Component */}
        <SecurityDisclosureCard />

        {/* SLA & Safe Harbor Breakdown */}
        <Card className="border-zinc-800 bg-zinc-950/80">
          <CardHeader>
            <CardTitle className="text-lg font-bold flex items-center space-x-2">
              <Clock className="h-5 w-5 text-amber-400" />
              <span>Response SLAs & Good-Faith Safe Harbor</span>
            </CardTitle>
          </CardHeader>

          <CardContent className="space-y-6 text-xs text-zinc-300">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-center">
              <div className="p-4 rounded-xl border border-zinc-800 bg-zinc-900/40">
                <div className="text-2xl font-bold text-emerald-400 font-mono">24 Hours</div>
                <div className="text-zinc-400 mt-1">Initial Triage SLA</div>
              </div>
              <div className="p-4 rounded-xl border border-zinc-800 bg-zinc-900/40">
                <div className="text-2xl font-bold text-amber-400 font-mono">72 Hours</div>
                <div className="text-zinc-400 mt-1">Remediation Plan SLA</div>
              </div>
              <div className="p-4 rounded-xl border border-zinc-800 bg-zinc-900/40">
                <div className="text-2xl font-bold text-blue-400 font-mono">14 Days</div>
                <div className="text-zinc-400 mt-1">Resolution & Patch SLA</div>
              </div>
            </div>

            <div className="space-y-3">
              <h4 className="font-bold text-zinc-100 text-sm flex items-center space-x-2">
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
                <span>Good-Faith Safe Harbor Principles</span>
              </h4>
              <ul className="space-y-2 text-zinc-400 pl-4 list-disc">
                <li>We will not pursue legal action against researchers operating within scope and good faith guidelines.</li>
                <li>Researchers must refrain from accessing, modifying, or deleting customer data.</li>
                <li>Do not execute Denial of Service (DoS/DDoS) attacks or social engineering against Vulnova personnel.</li>
                <li>Provide reasonable time for Vulnova to remediate vulnerabilities before public disclosure.</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
