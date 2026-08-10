"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Lock, ShieldAlert, ArrowLeft, ShieldCheck } from "lucide-react";
import { getCurrentUser, isRouteAllowed, UserRole } from "@/lib/auth";
import { Button } from "@/components/ui/button";

interface PermissionGateProps {
  children: React.ReactNode;
}

export function PermissionGate({ children }: PermissionGateProps) {
  const pathname = usePathname();
  const [role, setRole] = useState<UserRole>("SECURITY_ANALYST");
  const [authorized, setAuthorized] = useState<boolean>(true);

  useEffect(() => {
    const user = getCurrentUser();
    setRole(user.role);
    const allowed = isRouteAllowed(pathname || "", user.role);
    setAuthorized(allowed);
  }, [pathname]);

  if (!authorized) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center p-6 text-center space-y-6">
        <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-red-950/80 border border-red-800 text-red-500 shadow-2xl shadow-red-950/60">
          <Lock className="h-8 w-8 animate-pulse" />
        </div>

        <div className="space-y-2 max-w-md">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-red-950/60 border border-red-800/40 text-[11px] font-mono text-red-400 font-bold uppercase tracking-widest">
            <ShieldAlert className="h-3.5 w-3.5" />
            <span>HTTP 403 — ACCESS FORBIDDEN</span>
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Restricted Enterprise Access
          </h1>

          <p className="text-xs sm:text-sm text-zinc-400 leading-relaxed">
            Your current assigned role (<span className="text-red-400 font-mono font-bold">{role}</span>) does not possess permission to view or manage this security control module.
          </p>
        </div>

        <div className="p-4 rounded-xl border border-zinc-800 bg-zinc-900/60 text-xs text-zinc-400 font-mono max-w-sm w-full space-y-1">
          <div className="flex justify-between">
            <span className="text-zinc-500">Attempted Route:</span>
            <span className="text-zinc-200">{pathname}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-zinc-500">Current Role:</span>
            <span className="text-red-400 font-bold">{role}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-zinc-500">Required Role:</span>
            <span className="text-emerald-400 font-bold">ADMIN / OWNER</span>
          </div>
        </div>

        <div className="flex items-center space-x-4 pt-2">
          <Link href="/dashboard">
            <Button variant="primary" size="md" className="shadow-lg shadow-red-950/60">
              <ArrowLeft className="mr-2 h-4 w-4" />
              <span>Return to SOC Dashboard</span>
            </Button>
          </Link>
          <Link href="/trust">
            <Button variant="outline" size="md">
              <ShieldCheck className="mr-2 h-4 w-4 text-emerald-400" />
              <span>View Access Policies</span>
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
