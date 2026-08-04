"use client";

import React, { useEffect, useState } from "react";
import { AdminService, RolePermissionMatrixResponse } from "@/services/admin.service";
import { RolePermissionMatrix } from "@/components/settings/role-permission-matrix";

export default function SettingsRolesPage() {
  const [matrix, setMatrix] = useState<RolePermissionMatrixResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadMatrix() {
      try {
        setLoading(true);
        const data = await AdminService.getRolePermissionMatrix();
        setMatrix(data);
      } catch (err: any) {
        setError(err.message || "Failed to load role permission matrix.");
      } finally {
        setLoading(false);
      }
    }

    loadMatrix();
  }, []);

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center text-sm text-zinc-400">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-red-500 border-t-transparent mr-3" />
        <span>Loading Role Permission Matrix...</span>
      </div>
    );
  }

  if (error || !matrix) {
    return (
      <div className="p-6 rounded-xl border border-red-500/20 bg-red-500/10 text-red-400 text-sm">
        {error || "Role matrix not found."}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="border-b border-zinc-800 pb-4">
        <h1 className="text-2xl font-bold text-zinc-100">
          RBAC Role & Permission Boundary Matrix
        </h1>
        <p className="text-xs text-zinc-400 mt-1">
          Inspect granular resource permission boundaries across OWNER, ADMIN, SECURITY_ANALYST, and VIEWER roles.
        </p>
      </div>

      <RolePermissionMatrix matrix={matrix} />
    </div>
  );
}
