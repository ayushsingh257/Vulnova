"use client";

import React, { useState } from "react";
import Link from "next/link";
import { ShieldAlert, Building2, Mail, User, CheckCircle2, ArrowRight } from "lucide-react";
import { TrustHeader } from "@/components/trust/trust-header";

export default function SignupPage() {
  const [submitted, setSubmitted] = useState(false);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [targetCount, setTargetCount] = useState("10-50");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 font-sans antialiased flex flex-col selection:bg-red-500/30">
      <TrustHeader />

      <main className="flex-1 flex items-center justify-center p-6 max-w-lg mx-auto w-full my-auto">
        <div className="w-full bg-zinc-900/90 border border-zinc-800 rounded-2xl p-8 space-y-6 shadow-2xl backdrop-blur-xl">
          <div className="text-center space-y-2">
            <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-red-600/20 border border-red-500/40 text-red-500 shadow-md mb-2">
              <ShieldAlert className="h-6 w-6 animate-pulse" />
            </div>
            <h1 className="text-2xl font-extrabold text-white tracking-tight">
              Request Enterprise SOC Access
            </h1>
            <p className="text-xs text-zinc-400">
              Schedule an enterprise trial or request dedicated SOC tenant provisioning.
            </p>
          </div>

          {submitted ? (
            <div className="text-center space-y-4 p-6 rounded-xl border border-emerald-900/60 bg-emerald-950/20">
              <CheckCircle2 className="h-12 w-12 text-emerald-400 mx-auto" />
              <h2 className="text-lg font-bold text-white">Access Request Received!</h2>
              <p className="text-xs text-zinc-300">
                Our SecOps architecture team will review your application and send dedicated SOC platform credentials to <span className="font-bold text-emerald-400">{email}</span> within 2 hours.
              </p>
              <Link
                href="/login"
                className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg bg-emerald-950 border border-emerald-800 text-xs font-bold text-emerald-400 hover:bg-emerald-900"
              >
                <span>Proceed to Login</span>
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-zinc-400 font-semibold mb-1">Full Name</label>
                <div className="relative">
                  <User className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
                  <input
                    type="text"
                    required
                    placeholder="Jane Doe"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 rounded-lg border border-zinc-800 bg-zinc-950 text-zinc-200 focus:outline-none focus:border-red-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-zinc-400 font-semibold mb-1">Work Email Address</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
                  <input
                    type="email"
                    required
                    placeholder="jane@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 rounded-lg border border-zinc-800 bg-zinc-950 text-zinc-200 focus:outline-none focus:border-red-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-zinc-400 font-semibold mb-1">Company / Organization</label>
                <div className="relative">
                  <Building2 className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
                  <input
                    type="text"
                    required
                    placeholder="Acme Enterprise Inc"
                    value={company}
                    onChange={(e) => setCompany(e.target.value)}
                    className="w-full pl-9 pr-3 py-2 rounded-lg border border-zinc-800 bg-zinc-950 text-zinc-200 focus:outline-none focus:border-red-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-zinc-400 font-semibold mb-1">Target Environments Count</label>
                <select
                  value={targetCount}
                  onChange={(e) => setTargetCount(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-zinc-800 bg-zinc-950 text-zinc-200 focus:outline-none focus:border-red-500"
                >
                  <option value="1-10">1 - 10 Target Assets</option>
                  <option value="10-50">10 - 50 Target Assets</option>
                  <option value="50-500">50 - 500 Target Assets (Enterprise Tier)</option>
                  <option value="500+">500+ Target Assets (Custom Infrastructure)</option>
                </select>
              </div>

              <button
                type="submit"
                className="w-full py-2.5 rounded-lg bg-red-950 border border-red-800 text-xs font-bold text-red-400 hover:bg-red-900 transition-colors shadow-lg flex items-center justify-center space-x-2"
              >
                <span>Request Enterprise Provisioning</span>
                <ArrowRight className="h-4 w-4" />
              </button>
            </form>
          )}

          <div className="pt-4 border-t border-zinc-800 text-center text-xs text-zinc-500">
            <span>Already have an account? </span>
            <Link href="/login" className="text-red-400 font-semibold hover:underline">
              Sign In
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
