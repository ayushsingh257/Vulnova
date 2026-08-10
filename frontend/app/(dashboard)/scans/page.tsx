"use client";

import * as React from "react";
import { PermissionGate } from "@/components/auth/permission-gate";
import { ScanListTable } from "@/components/scans/scan-list-table";
import { ScanDispatchModal } from "@/components/scans/scan-dispatch-modal";
import { Button } from "@/components/ui/button";
import { Play, Search, Filter } from "lucide-react";
import { ScansService, ScanJobItem } from "@/services/scans.service";

export default function ScansPage() {
  const [scans, setScans] = React.useState<ScanJobItem[]>([
    {
      id: "8d48aca2-c4b9-45b2-b42d-e6f2dbfdeb18",
      target_name: "Production API Gateway",
      environment: "PRODUCTION",
      masked_target_url: "https://a***.s***.e***.com",
      profile_name: "FULL_RECON",
      status: "ASSESSING",
      current_step: "Executing Active Security Plugins",
      progress_percentage: 65.0,
      findings_count: 4,
      started_at: new Date().toISOString(),
    },
    {
      id: "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      target_name: "Auth Service Staging",
      environment: "STAGING",
      masked_target_url: "https://a***.s***.d***.org",
      profile_name: "LIGHTWEIGHT_DAST",
      status: "COMPLETED",
      current_step: "Scan Completed Successfully",
      progress_percentage: 100.0,
      findings_count: 1,
      started_at: new Date(Date.now() - 3600000).toISOString(),
      completed_at: new Date().toISOString(),
    },
  ]);

  const [isModalOpen, setIsModalOpen] = React.useState(false);
  const [statusFilter, setStatusFilter] = React.useState<string | undefined>();
  const [search, setSearch] = React.useState("");

  const loadScans = React.useCallback(() => {
    ScansService.listScans(1, 20, statusFilter, search)
      .then((res) => {
        if (res && res.items && res.items.length > 0) {
          setScans(res.items);
        }
      })
      .catch((err) => {
        console.warn("Using active local scan state:", err);
      });
  }, [statusFilter, search]);

  React.useEffect(() => {
    loadScans();
  }, [loadScans]);

  return (
    <PermissionGate>
      <div className="flex flex-col gap-6">
          {/* Header */}
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-zinc-800 pb-4">
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight text-white flex items-center gap-2">
                Scan Execution Portal
              </h1>
              <p className="text-xs text-zinc-400 mt-1">
                Dispatch and monitor container-sandboxed DAST assessments across active scopes.
              </p>
            </div>
            <Button
              onClick={() => setIsModalOpen(true)}
              className="bg-red-600 hover:bg-red-500 text-white font-bold text-xs gap-2 shadow-lg shadow-red-950/60"
            >
              <Play className="h-3.5 w-3.5 fill-current" />
              Dispatch New Scan
            </Button>
          </div>

          {/* Controls Bar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
              <span className="text-xs text-zinc-500 font-mono flex items-center gap-1 mr-2">
                <Filter className="h-3 w-3" /> Status:
              </span>
              {["ALL", "ASSESSING", "COMPLETED", "FAILED"].map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st === "ALL" ? undefined : st)}
                  className={`px-3 py-1 rounded-md text-xs font-mono transition-colors ${
                    (st === "ALL" && !statusFilter) || statusFilter === st
                      ? "border border-red-500 bg-red-950/40 text-red-400 font-bold"
                      : "border border-zinc-800 bg-zinc-900/60 text-zinc-400 hover:text-zinc-200"
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>

            <div className="relative w-full sm:w-64">
              <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-zinc-500" />
              <input
                type="text"
                placeholder="Search scope..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 rounded-lg border border-zinc-800 bg-zinc-900/80 text-xs text-zinc-200 focus:outline-none focus:border-red-500"
              />
            </div>
          </div>

          {/* Scan List Data Table */}
          <ScanListTable scans={scans} />

          {/* Dispatch Modal */}
          <ScanDispatchModal
            isOpen={isModalOpen}
            onClose={() => setIsModalOpen(false)}
            onScanDispatched={loadScans}
          />
      </div>
    </PermissionGate>
  );
}
